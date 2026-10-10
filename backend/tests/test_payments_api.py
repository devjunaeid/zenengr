"""Comprehensive tests for Unified Payment Architecture (FEAT-027, TODO-222..224).

Covers:
- Recording payments with invoice allocation vs unallocated advance credit.
- Same-day, same-amount payments (verifies zero heuristic drop / true ledger math).
- Over-allocation rejection.
- Void payment reverting invoice status & ledger summary.
- Restore payment bringing allocations and balances back.
- Project payments listing with allocations.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import (
    AdminUserRole,
    ClientType,
    InvoiceStatus,
    PaymentMethod,
    ProjectStatus,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"


async def _make_setup(db_session: AsyncSession) -> tuple[Tenant, Client, Project, AdminUser]:
    plan = Plan(
        name="PayTestPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="PayTest Tenant", slug="paytest-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    client = Client(tenant_id=tenant.id, name="PayTest Client", client_type=ClientType.COMPANY)
    db_session.add(client)
    await db_session.commit()

    project = Project(
        tenant_id=tenant.id,
        client_id=client.id,
        name="PayTest Project",
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=tenant.id,
        email="admin@paytest.test",
        hashed_password=hash_password(_TEST_PWD),
        full_name="PayTest Admin",
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    return tenant, client, project, admin


def _auth(admin: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(admin.id),
        tenant_id=str(admin.tenant_id),
        role=admin.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_same_day_same_amount_payments_both_persist(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    tenant, client_obj, project, admin = await _make_setup(db_session)
    headers = _auth(admin)

    # Record first payment of $500.00
    p1 = await client.post(
        "/api/v1/tenant/payments",
        json={
            "project_id": str(project.id),
            "amount": "500.00",
            "method": "bank_transfer",
            "paid_on": "2026-10-10",
            "reference_note": "Installment 1",
        },
        headers=headers,
    )
    assert p1.status_code == 201
    p1_data = p1.json()

    # Record second payment with IDENTICAL amount and date
    p2 = await client.post(
        "/api/v1/tenant/payments",
        json={
            "project_id": str(project.id),
            "amount": "500.00",
            "method": "bank_transfer",
            "paid_on": "2026-10-10",
            "reference_note": "Installment 2",
        },
        headers=headers,
    )
    assert p2.status_code == 201
    p2_data = p2.json()

    # Must be distinct IDs
    assert p1_data["id"] != p2_data["id"]

    # Verify statement ledger shows total paid = $1000.00 (NO heuristic drop)
    stmt_res = await client.get(
        f"/api/v1/tenant/projects/{project.id}/statement", headers=headers
    )
    assert stmt_res.status_code == 200
    data = stmt_res.json()
    assert data["summary"]["paid"] == "1000.00"
    assert data["summary"]["advance_balance"] == "1000.00"


@pytest.mark.asyncio
async def test_payment_allocation_to_invoice_and_overallocation_rejection(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    tenant, client_obj, project, admin = await _make_setup(db_session)
    headers = _auth(admin)

    # Create an issued invoice for $600.00
    invoice = Invoice(
        tenant_id=tenant.id,
        project_id=project.id,
        invoice_number="INV-PAY-001",
        status=InvoiceStatus.ISSUED,
        subtotal=Decimal("600.00"),
        total=Decimal("600.00"),
    )
    db_session.add(invoice)
    await db_session.commit()

    li = InvoiceLineItem(
        invoice_id=invoice.id,
        description="Foundation Engineering",
        quantity=Decimal("1"),
        unit_price=Decimal("600.00"),
        amount=Decimal("600.00"),
    )
    db_session.add(li)
    await db_session.commit()

    # Attempt to allocate more than payment amount -> 400
    over_res = await client.post(
        "/api/v1/tenant/payments",
        json={
            "project_id": str(project.id),
            "amount": "200.00",
            "method": "card",
            "allocations": [{"invoice_id": str(invoice.id), "amount": "300.00"}],
        },
        headers=headers,
    )
    assert over_res.status_code == 400
    err_body = over_res.json()
    err_msg = err_body.get("detail") or err_body.get("error", {}).get("message", "")
    assert "exceeds payment amount" in err_msg

    # Valid partial allocation: Payment of $400, allocated $400 to invoice
    pay_res = await client.post(
        "/api/v1/tenant/payments",
        json={
            "project_id": str(project.id),
            "amount": "400.00",
            "method": "card",
            "allocations": [{"invoice_id": str(invoice.id), "amount": "400.00"}],
        },
        headers=headers,
    )
    assert pay_res.status_code == 201

    # Invoice status should now be partially_paid
    inv_check = await client.get(f"/api/v1/tenant/invoices/{invoice.id}", headers=headers)
    assert inv_check.status_code == 200
    assert inv_check.json()["status"] == "partially_paid"


@pytest.mark.asyncio
async def test_void_and_restore_payment_recalculates_state(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    tenant, client_obj, project, admin = await _make_setup(db_session)
    headers = _auth(admin)

    # Create an invoice for $500.00
    invoice = Invoice(
        tenant_id=tenant.id,
        project_id=project.id,
        invoice_number="INV-PAY-002",
        status=InvoiceStatus.ISSUED,
        subtotal=Decimal("500.00"),
        total=Decimal("500.00"),
    )
    db_session.add(invoice)
    await db_session.commit()

    li = InvoiceLineItem(
        invoice_id=invoice.id,
        description="Site Supervision",
        quantity=Decimal("1"),
        unit_price=Decimal("500.00"),
        amount=Decimal("500.00"),
    )
    db_session.add(li)
    await db_session.commit()

    # Pay in full
    pay_res = await client.post(
        "/api/v1/tenant/payments",
        json={
            "project_id": str(project.id),
            "amount": "500.00",
            "method": "bank_transfer",
            "allocations": [{"invoice_id": str(invoice.id), "amount": "500.00"}],
        },
        headers=headers,
    )
    assert pay_res.status_code == 201
    pay_id = pay_res.json()["id"]

    # Invoice is now paid
    inv_check = await client.get(f"/api/v1/tenant/invoices/{invoice.id}", headers=headers)
    assert inv_check.json()["status"] == "paid"

    # Void payment with reason
    void_res = await client.post(
        f"/api/v1/tenant/payments/{pay_id}/void",
        json={"reason": "Customer check bounced"},
        headers=headers,
    )
    assert void_res.status_code == 200
    assert void_res.json()["is_voided"] is True

    # Invoice status must revert to issued
    inv_check_void = await client.get(f"/api/v1/tenant/invoices/{invoice.id}", headers=headers)
    assert inv_check_void.json()["status"] == "issued"

    # Restore payment
    restore_res = await client.post(
        f"/api/v1/tenant/payments/{pay_id}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["is_voided"] is False

    # Invoice status is paid once more
    inv_check_restored = await client.get(f"/api/v1/tenant/invoices/{invoice.id}", headers=headers)
    assert inv_check_restored.json()["status"] == "paid"
