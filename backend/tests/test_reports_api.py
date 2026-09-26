"""Integration tests for company global ledger & analytics reporting (FEAT-025, TODO-213)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    InvoiceStatus,
    PaymentMethod,
    TenantStatus,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.transaction import PaymentAllocation, Transaction

_TEST_PWD = "testpass123!"


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"Plan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=20,
        max_active_projects=50,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant(session: AsyncSession, plan_id: uuid.UUID) -> Tenant:
    tenant = Tenant(
        business_name="Analytics Corp",
        slug=f"analytics-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_admin(
    session: AsyncSession,
    email: str,
    role: AdminUserRole,
    tenant_id: uuid.UUID | None = None,
) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=email,
        full_name=f"User {role.value}",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_company_ledger_rbac_guard(client: AsyncClient, db_session: AsyncSession):
    """Admin and Manager can view reports; Employee is 403 Forbidden."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)

    email_a = f"admin-{uuid.uuid4().hex[:6]}@test.com"
    email_m = f"mgr-{uuid.uuid4().hex[:6]}@test.com"
    email_e = f"emp-{uuid.uuid4().hex[:6]}@test.com"

    admin = await _create_admin(db_session, email_a, AdminUserRole.ADMIN, tenant.id)
    manager = await _create_admin(db_session, email_m, AdminUserRole.MANAGER, tenant.id)
    employee = await _create_admin(db_session, email_e, AdminUserRole.EMPLOYEE, tenant.id)

    # 1. Admin gets 200
    head_a = await _auth_header(admin)
    res_admin = await client.get("/api/v1/tenant/reports/company-ledger", headers=head_a)
    assert res_admin.status_code == 200

    # 2. Manager gets 200
    head_m = await _auth_header(manager)
    res_mgr = await client.get("/api/v1/tenant/reports/company-ledger", headers=head_m)
    assert res_mgr.status_code == 200

    # 3. Employee gets 403 Forbidden
    head_e = await _auth_header(employee)
    res_emp = await client.get("/api/v1/tenant/reports/company-ledger", headers=head_e)
    assert res_emp.status_code == 403


@pytest.mark.asyncio
async def test_company_ledger_aggregations_and_slicing(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies KPI summaries, timeline, projects, and clients rollups."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    email_adm = f"admin-{uuid.uuid4().hex[:6]}@test.com"
    admin = await _create_admin(db_session, email_adm, AdminUserRole.ADMIN, tenant.id)
    headers = await _auth_header(admin)

    # Create Client
    c1 = Client(
        tenant_id=tenant.id,
        name="Acme Corp",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    db_session.add(c1)
    await db_session.commit()
    await db_session.refresh(c1)

    # Create Service
    s1 = Service(
        tenant_id=tenant.id,
        name="Architecture Design",
        default_price=Decimal("1200.00"),
        is_active=True,
    )
    db_session.add(s1)
    await db_session.commit()
    await db_session.refresh(s1)

    # Create Project & attach service
    p1 = Project(
        tenant_id=tenant.id,
        name="Skyscraper Alpha",
        client_id=c1.id,
    )
    db_session.add(p1)
    await db_session.commit()
    await db_session.refresh(p1)

    ps1 = ProjectService(
        project_id=p1.id,
        service_id=s1.id,
        price_at_attachment=Decimal("1200.00"),
    )
    db_session.add(ps1)
    await db_session.commit()
    await db_session.refresh(ps1)

    # Create Issued Invoice for $1200
    inv1 = Invoice(
        tenant_id=tenant.id,
        project_id=p1.id,
        invoice_number="INV-2026-9001",
        status=InvoiceStatus.ISSUED,
        issue_date=date.today(),
        subtotal=Decimal("1200.00"),
        tax_total=Decimal("0.00"),
        total=Decimal("1200.00"),
    )
    db_session.add(inv1)
    await db_session.commit()
    await db_session.refresh(inv1)

    li1 = InvoiceLineItem(
        invoice_id=inv1.id,
        service_id=s1.id,
        project_service_id=ps1.id,
        description="Architecture Design",
        quantity=Decimal("1.00"),
        unit_price=Decimal("1200.00"),
        amount=Decimal("1200.00"),
    )
    db_session.add(li1)
    await db_session.commit()
    await db_session.refresh(li1)

    # Record Payment of $500
    tx1 = Transaction(
        invoice_id=inv1.id,
        amount=Decimal("500.00"),
        method=PaymentMethod.BANK_TRANSFER,
        reference_note="Down payment",
        recorded_by_id=admin.id,
    )
    db_session.add(tx1)
    await db_session.commit()
    await db_session.refresh(tx1)

    alloc1 = PaymentAllocation(
        transaction_id=tx1.id,
        line_item_id=li1.id,
        amount=Decimal("500.00"),
    )
    db_session.add(alloc1)
    inv1.status = InvoiceStatus.PARTIALLY_PAID
    await db_session.commit()

    # Query Company Ledger endpoint
    res = await client.get("/api/v1/tenant/reports/company-ledger", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Summary verification
    summary = data["summary"]
    assert summary["new_projects_count"] >= 1
    assert summary["new_clients_count"] >= 1
    assert summary["new_services_count"] >= 1
    assert summary["total_invoiced"] == "1200.00"
    assert summary["total_collected"] == "500.00"
    assert summary["total_due"] == "700.00"

    # Timeline verification
    timeline = data["timeline"]
    assert len(timeline) >= 1
    current_bucket = timeline[0]
    assert current_bucket["new_projects"] >= 1
    assert current_bucket["invoiced_amount"] == "1200.00"
    assert current_bucket["collected_amount"] == "500.00"

    # Project breakdown verification
    projects = data["projects"]
    assert any(p["project_id"] == str(p1.id) and p["balance_due"] == "700.00" for p in projects)

    # Client breakdown verification
    clients = data["clients"]
    assert any(c["client_id"] == str(c1.id) and c["total_due"] == "700.00" for c in clients)

    # Filter by specific client_id
    res_client = await client.get(
        f"/api/v1/tenant/reports/company-ledger?client_id={c1.id}", headers=headers
    )
    assert res_client.status_code == 200
    c_data = res_client.json()
    assert len(c_data["clients"]) == 1
    assert c_data["clients"][0]["name"] == "Acme Corp"
