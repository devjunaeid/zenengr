"""Tests for Direct Project Payments / Transactions & Statement Synchronization.

Covers:
- Recording direct payments on a project without needing an invoice.
- Realtime ledger reflection (entries + updated due & advance balance).
- Live Statement API & PDF reflection of direct payments.
- Input validation (amount > 0).
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
from app.models.client_user import ClientUser
from app.models.enums import AdminUserRole, ClientStatus, ClientType, ProjectStatus, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import ledger as ledger_service

_TEST_PWD = "testpass123!"


async def _make_setup(db_session: AsyncSession) -> tuple[Tenant, Client, Project, AdminUser, ClientUser]:
    plan = Plan(
        name="ProjectPaymentPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="Payment Tenant", slug="payment-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    client = Client(tenant_id=tenant.id, name="Payment Client", client_type=ClientType.COMPANY)
    db_session.add(client)
    await db_session.commit()

    project = Project(
        tenant_id=tenant.id,
        client_id=client.id,
        name="Payment Project",
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=tenant.id,
        email="admin@payment-tenant.com",
        hashed_password=hash_password(_TEST_PWD),
        full_name="Payment Admin",
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)

    client_user = ClientUser(
        tenant_id=tenant.id,
        client_id=client.id,
        email="portal@payment-client.com",
        hashed_password=hash_password(_TEST_PWD),
        full_name="Payment Client User",
        is_active=True,
    )
    db_session.add(client_user)
    await db_session.commit()

    return tenant, client, project, admin, client_user


def _admin_headers(admin: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(admin.id),
        tenant_id=str(admin.tenant_id),
        role=admin.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_record_direct_project_payment_and_sync_statement(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tenant, client_rec, project, admin, _ = await _make_setup(db_session)
    headers = _admin_headers(admin)

    # 1. Attach a service for $1000.00
    svc = Service(tenant_id=tenant.id, name="Structural Design", default_price=Decimal("1000.00"), is_active=True)
    db_session.add(svc)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/services",
        json={"service_id": str(svc.id)},
        headers=headers,
    )
    assert res.status_code == 201

    # Check ledger initially: Subtotal = 1000.00, Paid = 0.00, Due = 1000.00
    res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["subtotal"] == "1000.00"
    assert data["summary"]["paid"] == "0.00"
    assert data["summary"]["due"] == "1000.00"
    assert data["summary"]["advance_balance"] == "0.00"

    # 2. Record direct project payment of $400.00 without issuing any invoice
    pay_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/payments",
        json={
            "amount": "400.00",
            "method": "bank_transfer",
            "entry_date": "2026-08-25",
            "reference_note": "Advance wire transfer",
        },
        headers=headers,
    )
    assert pay_res.status_code == 201
    pay_data = pay_res.json()
    assert pay_data["type"] == "payment"
    assert pay_data["amount"] == "400.00"
    assert "Bank Transfer" in pay_data["description"]
    assert "Advance wire transfer" in pay_data["description"]

    # 3. Statement reflects payment: Paid = 400.00, Due = 600.00
    res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["subtotal"] == "1000.00"
    assert data["summary"]["paid"] == "400.00"
    assert data["summary"]["due"] == "600.00"
    assert data["summary"]["advance_balance"] == "0.00"
    assert len(data["entries"]) == 2
    assert any(e["type"] == "payment" and e["amount"] == "400.00" for e in data["entries"])

    # 4. Record additional direct payment of $800.00 -> total paid $1200.00 -> advance $200.00
    pay2_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/payments",
        json={
            "amount": "800.00",
            "method": "card",
            "reference_note": "Credit card payment",
        },
        headers=headers,
    )
    assert pay2_res.status_code == 201

    res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["subtotal"] == "1000.00"
    assert data["summary"]["paid"] == "1200.00"
    assert data["summary"]["due"] == "0.00"
    assert data["summary"]["advance_balance"] == "200.00"

    # 5. Check statement PDF generation includes direct payments
    pdf_res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 100


@pytest.mark.asyncio
async def test_direct_project_payment_validation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tenant, client_rec, project, admin, _ = await _make_setup(db_session)
    headers = _admin_headers(admin)

    # Invalid amount <= 0
    res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/payments",
        json={"amount": "0.00", "method": "cash"},
        headers=headers,
    )
    assert res.status_code == 422
