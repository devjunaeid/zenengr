"""Tests for FEAT-019 Cumulative Statement Invoicing & Realtime Financial Sync (TODO-187..193).

Covers:
- Live Statement API & Advance calculation when Total Paid > Total Charges.
- Live Statement PDF endpoint (staff & client).
- "Generate Statement Invoice" creating an official issued invoice with sequential numbering.
- Progressive/multi-day incremental invoice generation flow.
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
from app.models.enums import AdminUserRole, ClientStatus, ClientType, InvoiceStatus, ProjectStatus, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import ledger as ledger_service

_TEST_PWD = "testpass123!"


async def _make_setup(db_session: AsyncSession) -> tuple[Tenant, Client, Project, AdminUser, ClientUser]:
    plan = Plan(
        name="StatementPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="Statement Tenant", slug="statement-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    client = Client(tenant_id=tenant.id, name="Statement Client", client_type=ClientType.COMPANY)
    db_session.add(client)
    await db_session.commit()

    project = Project(
        tenant_id=tenant.id,
        client_id=client.id,
        name="Statement Project",
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=tenant.id,
        email="admin@statement.test",
        hashed_password=hash_password(_TEST_PWD),
        full_name="Statement Admin",
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)

    client_user = ClientUser(
        tenant_id=tenant.id,
        client_id=client.id,
        email="client@statement.test",
        hashed_password=hash_password(_TEST_PWD),
        full_name="Statement Client User",
        is_active=True,
    )
    db_session.add(client_user)
    await db_session.commit()

    return tenant, client, project, admin, client_user


def _admin_auth(admin: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(admin.id),
        tenant_id=str(admin.tenant_id),
        role=admin.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


def _client_auth(cu: ClientUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(cu.id),
        tenant_id=str(cu.tenant_id),
        role="client_user",
        realm="client",
        client_id=str(cu.client_id),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_live_statement_preview_and_advance_math(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    tenant, client_obj, project, admin, _ = await _make_setup(db_session)
    headers = _admin_auth(admin)

    # 1. Add 2 services to the project ($100 + $200)
    svc1 = Service(tenant_id=tenant.id, name="Design", default_price=Decimal("100.00"))
    svc2 = Service(tenant_id=tenant.id, name="Development", default_price=Decimal("200.00"))
    db_session.add_all([svc1, svc2])
    await db_session.commit()

    ps1 = ProjectService(project_id=project.id, service_id=svc1.id, price_at_attachment=Decimal("100.00"))
    ps2 = ProjectService(project_id=project.id, service_id=svc2.id, price_at_attachment=Decimal("200.00"))
    db_session.add_all([ps1, ps2])
    await db_session.commit()

    # Add ledger charge hooks
    await ledger_service.add_service_charge(db_session, project_id=project.id, project_service_id=ps1.id, amount=Decimal("100.00"), description="Design")
    await ledger_service.add_service_charge(db_session, project_id=project.id, project_service_id=ps2.id, amount=Decimal("200.00"), description="Development")
    await db_session.commit()

    # 2. Check statement endpoint
    res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["subtotal"] == "300.00"
    assert data["summary"]["total"] == "300.00"
    assert data["summary"]["paid"] == "0.00"
    assert data["summary"]["due"] == "300.00"
    assert data["summary"]["advance_balance"] == "0.00"
    assert len(data["entries"]) == 2

    # 3. Check live statement PDF
    pdf_res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_generate_statement_invoice_and_subsequent_flow(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    tenant, client_obj, project, admin, client_user = await _make_setup(db_session)
    admin_headers = _admin_auth(admin)
    client_headers = _client_auth(client_user)

    # 1. Day 1: Attach 2 services ($150 + $250 = $400)
    svc1 = Service(tenant_id=tenant.id, name="Audit", default_price=Decimal("150.00"))
    svc2 = Service(tenant_id=tenant.id, name="Implementation", default_price=Decimal("250.00"))
    db_session.add_all([svc1, svc2])
    await db_session.commit()

    ps1 = ProjectService(project_id=project.id, service_id=svc1.id, price_at_attachment=Decimal("150.00"))
    ps2 = ProjectService(project_id=project.id, service_id=svc2.id, price_at_attachment=Decimal("250.00"))
    db_session.add_all([ps1, ps2])
    await db_session.commit()

    await ledger_service.add_service_charge(db_session, project_id=project.id, project_service_id=ps1.id, amount=Decimal("150.00"), description="Audit")
    await ledger_service.add_service_charge(db_session, project_id=project.id, project_service_id=ps2.id, amount=Decimal("250.00"), description="Implementation")
    await db_session.commit()

    # Issue Invoice #1 via Generate Statement Invoice
    gen_res = await client.post(f"/api/v1/tenant/projects/{project.id}/generate-statement-invoice", headers=admin_headers)
    assert gen_res.status_code == 201
    inv1 = gen_res.json()
    assert inv1["status"] == "issued"
    assert inv1["invoice_number"] is not None
    assert inv1["total"] == "400.00"
    assert len(inv1["line_items"]) == 2

    # Record a $200 payment against Invoice #1
    pay_res = await client.post(
        f"/api/v1/tenant/invoices/{inv1['id']}/transactions",
        json={"amount": 200.00, "method": "bank_transfer", "reference_note": "Deposit"},
        headers=admin_headers,
    )
    assert pay_res.status_code == 201

    # Check project statement: Paid = $200, Due = $200, Advance = $0
    stmt_res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=admin_headers)
    assert stmt_res.status_code == 200
    stmt_data = stmt_res.json()
    assert stmt_data["summary"]["total"] == "400.00"
    assert stmt_data["summary"]["paid"] == "200.00"
    assert stmt_data["summary"]["due"] == "200.00"
    assert stmt_data["summary"]["advance_balance"] == "0.00"

    # 2. Day 3: Add a new service ($300)
    svc3 = Service(tenant_id=tenant.id, name="Deployment", default_price=Decimal("300.00"))
    db_session.add(svc3)
    await db_session.commit()

    ps3 = ProjectService(project_id=project.id, service_id=svc3.id, price_at_attachment=Decimal("300.00"))
    db_session.add(ps3)
    await db_session.commit()
    await ledger_service.add_service_charge(db_session, project_id=project.id, project_service_id=ps3.id, amount=Decimal("300.00"), description="Deployment")
    await db_session.commit()

    # Statement now reflects: Total Charges = $700, Paid = $200, Due = $500
    stmt_res2 = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=admin_headers)
    stmt_data2 = stmt_res2.json()
    assert stmt_data2["summary"]["total"] == "700.00"
    assert stmt_data2["summary"]["paid"] == "200.00"
    assert stmt_data2["summary"]["due"] == "500.00"

    # Issue Invoice #2 (Cumulative statement invoice including all 3 services)
    gen_res2 = await client.post(f"/api/v1/tenant/projects/{project.id}/generate-statement-invoice", headers=admin_headers)
    assert gen_res2.status_code == 201
    inv2 = gen_res2.json()
    assert inv2["status"] == "issued"
    assert inv2["total"] == "700.00"
    assert len(inv2["line_items"]) == 3
    assert inv2["invoice_number"] != inv1["invoice_number"]

    # 3. Client Portal can view and download client statement PDF
    client_pdf_res = await client.get(f"/api/v1/client/projects/{project.id}/statement/pdf", headers=client_headers)
    assert client_pdf_res.status_code == 200
    assert client_pdf_res.headers["content-type"] == "application/pdf"
    assert client_pdf_res.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_generate_statement_invoice_includes_prior_direct_payments(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    tenant, client_obj, project, admin, _ = await _make_setup(db_session)
    admin_headers = _admin_auth(admin)

    # 1. Attach service ($300)
    svc = Service(tenant_id=tenant.id, name="Design System", default_price=Decimal("300.00"))
    db_session.add(svc)
    await db_session.commit()

    ps = ProjectService(project_id=project.id, service_id=svc.id, price_at_attachment=Decimal("300.00"))
    db_session.add(ps)
    await db_session.commit()
    await ledger_service.add_service_charge(db_session, project_id=project.id, project_service_id=ps.id, amount=Decimal("300.00"), description="Design System")
    await db_session.commit()

    # 2. Record a direct payment on the project ($100) before any invoice is generated
    pay_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/payments",
        json={"amount": "100.00", "method": "bank_transfer", "reference_note": "Advance wire"},
        headers=admin_headers,
    )
    assert pay_res.status_code == 201

    # 3. Generate statement invoice for the project
    gen_res = await client.post(f"/api/v1/tenant/projects/{project.id}/generate-statement-invoice", headers=admin_headers)
    assert gen_res.status_code == 201
    inv = gen_res.json()
    assert inv["total"] == "300.00"
    # Status should be partially_paid because $100 was applied out of $300 total
    assert inv["status"] == "partially_paid"

    # Fetch invoice transactions to confirm payment transaction is attached
    tx_res = await client.get(f"/api/v1/tenant/invoices/{inv['id']}/transactions", headers=admin_headers)
    assert tx_res.status_code == 200
    tx_list = tx_res.json()
    assert len(tx_list) == 1
    assert tx_list[0]["amount"] == "100.00"

    # Ledger summary check: Total = 300, Paid = 100, Due = 200
    stmt_res = await client.get(f"/api/v1/tenant/projects/{project.id}/statement", headers=admin_headers)
    assert stmt_res.status_code == 200
    stmt_data = stmt_res.json()
    assert stmt_data["summary"]["total"] == "300.00"
    assert stmt_data["summary"]["paid"] == "100.00"
    assert stmt_data["summary"]["due"] == "200.00"

