"""Tests for FEAT-022 Financial Corrections, Service Price Edits & Ledger Entry Management (TODO-201..TODO-203).

Covers:
- Updating attached service price (PATCH /tenant/projects/{id}/services/{service_id}).
- Verification of ledger charge update and draft invoice sync.
- Issued invoice locking guard on service price update.
- Updating and deleting manual ledger adjustments.
- Updating and deleting direct project payments.
- Deleting invoice payment transactions with invoice status recompute.
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
    TenantStatus,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import ledger as ledger_service

_TEST_PWD = "testpass123!"


def _admin_auth(admin: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(admin.id),
        tenant_id=str(admin.tenant_id),
        role=admin.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _setup_data(db_session: AsyncSession) -> tuple[Tenant, Client, Project, AdminUser, Service, ProjectService]:
    plan = Plan(
        name="CorrectionPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="Correction Tenant", slug="correction-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    client = Client(tenant_id=tenant.id, name="Correction Client", client_type=ClientType.COMPANY)
    db_session.add(client)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=tenant.id,
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Correction Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    project = Project(
        tenant_id=tenant.id,
        client_id=client.id,
        name="Correction Project",
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()

    service = Service(
        tenant_id=tenant.id,
        name="Web Design",
        default_price=Decimal("1000.00"),
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()

    ps = ProjectService(
        project_id=project.id,
        service_id=service.id,
        price_at_attachment=Decimal("1000.00"),
    )
    db_session.add(ps)
    await db_session.commit()

    # Add ledger charge
    await ledger_service.add_service_charge(
        db_session,
        project_id=project.id,
        project_service_id=ps.id,
        amount=Decimal("1000.00"),
        description="Web Design",
        actor_id=admin.id,
    )
    await db_session.commit()

    return tenant, client, project, admin, service, ps


@pytest.mark.asyncio
async def test_update_project_service_price(client: AsyncClient, db_session: AsyncSession):
    tenant, cl, project, admin, service, ps = await _setup_data(db_session)
    headers = _admin_auth(admin)

    # Create a draft invoice containing this service
    draft_inv = Invoice(
        tenant_id=tenant.id,
        project_id=project.id,
        status=InvoiceStatus.DRAFT,
    )
    db_session.add(draft_inv)
    await db_session.flush()
    line_item = InvoiceLineItem(
        invoice_id=draft_inv.id,
        project_service_id=ps.id,
        description="Web Design",
        quantity=Decimal("1"),
        unit_price=Decimal("1000.00"),
        amount=Decimal("1000.00"),
    )
    db_session.add(line_item)
    await db_session.commit()

    # Update price from 1000.00 to 1250.00
    res = await client.patch(
        f"/api/v1/tenant/projects/{project.id}/services/{ps.id}",
        json={"price": "1250.00"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["price_at_attachment"] == "1250.00"

    # Verify ledger summary
    ledger_res = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res.status_code == 200
    summary = ledger_res.json()["summary"]
    assert summary["subtotal"] == "1250.00"
    assert summary["total"] == "1250.00"

    # Verify draft invoice line item was synced
    await db_session.refresh(line_item)
    assert line_item.unit_price == Decimal("1250.00")
    assert line_item.amount == Decimal("1250.00")


@pytest.mark.asyncio
async def test_update_service_price_blocked_on_issued_invoice(client: AsyncClient, db_session: AsyncSession):
    tenant, cl, project, admin, service, ps = await _setup_data(db_session)
    headers = _admin_auth(admin)

    # Create an issued invoice containing this service
    issued_inv = Invoice(
        tenant_id=tenant.id,
        project_id=project.id,
        status=InvoiceStatus.ISSUED,
        invoice_number="INV-0099",
    )
    db_session.add(issued_inv)
    await db_session.flush()
    line_item = InvoiceLineItem(
        invoice_id=issued_inv.id,
        project_service_id=ps.id,
        description="Web Design",
        quantity=Decimal("1"),
        unit_price=Decimal("1000.00"),
        amount=Decimal("1000.00"),
    )
    db_session.add(line_item)
    await db_session.commit()

    # Attempting to update service price should be rejected with 409
    res = await client.patch(
        f"/api/v1/tenant/projects/{project.id}/services/{ps.id}",
        json={"price": "1500.00"},
        headers=headers,
    )
    assert res.status_code == 409
    assert "already billed" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_manual_adjustment_crud(client: AsyncClient, db_session: AsyncSession):
    tenant, cl, project, admin, _, _ = await _setup_data(db_session)
    headers = _admin_auth(admin)

    # 1. Create manual adjustment
    add_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/ledger/adjustments",
        json={"amount": "-200.00", "description": "Goodwill discount"},
        headers=headers,
    )
    assert add_res.status_code == 201
    entry_id = add_res.json()["id"]

    # Check ledger subtotal
    ledger_res = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res.json()["summary"]["subtotal"] == "800.00"

    # 2. Update manual adjustment to -100.00
    patch_res = await client.patch(
        f"/api/v1/tenant/projects/{project.id}/ledger/adjustments/{entry_id}",
        json={"amount": "-100.00", "description": "Corrected discount"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == "-100.00"
    assert patch_res.json()["description"] == "Corrected discount"

    # Verify updated ledger subtotal (1000 - 100 = 900)
    ledger_res2 = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res2.json()["summary"]["subtotal"] == "900.00"

    # 3. Delete manual adjustment
    del_res = await client.delete(
        f"/api/v1/tenant/projects/{project.id}/ledger/adjustments/{entry_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    # Verify ledger subtotal restored to 1000.00
    ledger_res3 = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res3.json()["summary"]["subtotal"] == "1000.00"


@pytest.mark.asyncio
async def test_project_payment_crud(client: AsyncClient, db_session: AsyncSession):
    tenant, cl, project, admin, _, _ = await _setup_data(db_session)
    headers = _admin_auth(admin)

    # 1. Record direct project payment
    pay_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/payments",
        json={"amount": "400.00", "method": "bank_transfer", "reference_note": "Ref #123"},
        headers=headers,
    )
    assert pay_res.status_code == 201
    entry_id = pay_res.json()["id"]

    ledger_res = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res.json()["summary"]["paid"] == "400.00"
    assert ledger_res.json()["summary"]["due"] == "600.00"

    # 2. Update payment amount to 500.00
    patch_res = await client.patch(
        f"/api/v1/tenant/projects/{project.id}/payments/{entry_id}",
        json={"amount": "500.00", "reference_note": "Corrected Ref #124"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == "500.00"

    ledger_res2 = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res2.json()["summary"]["paid"] == "500.00"
    assert ledger_res2.json()["summary"]["due"] == "500.00"

    # 3. Delete direct payment
    del_res = await client.delete(
        f"/api/v1/tenant/projects/{project.id}/payments/{entry_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    ledger_res3 = await client.get(
        f"/api/v1/tenant/projects/{project.id}/ledger",
        headers=headers,
    )
    assert ledger_res3.json()["summary"]["paid"] == "0.00"
    assert ledger_res3.json()["summary"]["due"] == "1000.00"


@pytest.mark.asyncio
async def test_delete_invoice_transaction(client: AsyncClient, db_session: AsyncSession):
    tenant, cl, project, admin, service, ps = await _setup_data(db_session)
    headers = _admin_auth(admin)

    # Create issued invoice of 1000.00
    invoice = Invoice(
        tenant_id=tenant.id,
        project_id=project.id,
        status=InvoiceStatus.ISSUED,
        invoice_number="INV-0055",
        subtotal=Decimal("1000.00"),
        total=Decimal("1000.00"),
    )
    db_session.add(invoice)
    await db_session.flush()
    line_item = InvoiceLineItem(
        invoice_id=invoice.id,
        project_service_id=ps.id,
        description="Web Design",
        quantity=Decimal("1"),
        unit_price=Decimal("1000.00"),
        amount=Decimal("1000.00"),
    )
    db_session.add(line_item)
    await db_session.commit()

    # Record full payment (1000.00) -> Invoice becomes PAID
    pay_res = await client.post(
        f"/api/v1/tenant/invoices/{invoice.id}/transactions",
        json={"amount": "1000.00", "method": "bank_transfer"},
        headers=headers,
    )
    assert pay_res.status_code == 201
    tx_id = pay_res.json()["id"]

    await db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.PAID

    # Delete transaction
    del_res = await client.delete(
        f"/api/v1/tenant/invoices/{invoice.id}/transactions/{tx_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    # Invoice status must revert to ISSUED
    await db_session.refresh(invoice)
    assert invoice.status == InvoiceStatus.ISSUED
