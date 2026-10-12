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
    LedgerEntryType,
    LedgerSourceType,
    PaymentKind,
    PaymentMethod,
    TenantStatus,
    TransactionDirection,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.ledger_entry import LedgerEntry
from app.models.payment import Payment
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


@pytest.mark.asyncio
async def test_company_ledger_sourced_from_ledger_not_invoice(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies reports source billing and receivables from LedgerEntry & Payment, not invoices.

    1. Ledger charges exist without any invoice -> report shows correct billed and due.
    2. Invoices (including multiple/statement invoices) do NOT inflate or alter ledger truth.
    """
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session, f"admin-{uuid.uuid4().hex[:6]}@test.com", AdminUserRole.ADMIN, tenant.id
    )
    headers = await _auth_header(admin)

    # 1. Create client & project
    c = Client(
        tenant_id=tenant.id,
        name="Nexus Engineering",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    p = Project(
        tenant_id=tenant.id,
        name="Harbor Bridge Inspection",
        client_id=c.id,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    # 2. Add LedgerEntry charge of $2000.00 directly to ledger (NO invoice)
    ch1 = LedgerEntry(
        project_id=p.id,
        type=LedgerEntryType.CHARGE,
        amount=Decimal("2000.00"),
        description="Core Structural Inspection",
        source_type=LedgerSourceType.PROJECT_SERVICE,
        entry_date=date.today(),
    )
    # Add manual ledger adjustment of $500.00
    adj1 = LedgerEntry(
        project_id=p.id,
        type=LedgerEntryType.CHARGE,
        amount=Decimal("500.00"),
        description="Hazardous Access Surcharge",
        source_type=LedgerSourceType.MANUAL_ADJUSTMENT,
        entry_date=date.today(),
    )
    db_session.add_all([ch1, adj1])
    await db_session.commit()

    # 3. Add direct Payment of $1000.00
    pay1 = Payment(
        tenant_id=tenant.id,
        client_id=c.id,
        project_id=p.id,
        kind=PaymentKind.RECEIPT,
        amount=Decimal("1000.00"),
        method=PaymentMethod.BANK_TRANSFER,
        paid_on=date.today(),
        recorded_by_id=admin.id,
    )
    db_session.add(pay1)
    await db_session.commit()

    # 4. Query report with ZERO invoices created
    res = await client.get("/api/v1/tenant/reports/company-ledger", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Summary: Billed $2500, Paid $1000, Due $1500 from ledger
    assert data["summary"]["total_invoiced"] == "2500.00"
    assert data["summary"]["total_collected"] == "1000.00"
    assert data["summary"]["total_due"] == "1500.00"

    # Project rollup
    proj_report = next((item for item in data["projects"] if item["project_id"] == str(p.id)), None)
    assert proj_report is not None
    assert proj_report["total_invoiced"] == "2500.00"
    assert proj_report["total_paid"] == "1000.00"
    assert proj_report["balance_due"] == "1500.00"

    # Client rollup
    cli_report = next((item for item in data["clients"] if item["client_id"] == str(c.id)), None)
    assert cli_report is not None
    assert cli_report["total_invoiced"] == "2500.00"
    assert cli_report["total_paid"] == "1000.00"
    assert cli_report["total_due"] == "1500.00"

    # 5. Now create multiple invoices (e.g. regular invoice + statement invoice) totaling $5000.00
    inv_reg = Invoice(
        tenant_id=tenant.id,
        project_id=p.id,
        invoice_number="INV-REG-001",
        status=InvoiceStatus.ISSUED,
        issue_date=date.today(),
        subtotal=Decimal("2500.00"),
        total=Decimal("2500.00"),
    )
    inv_stmt = Invoice(
        tenant_id=tenant.id,
        project_id=p.id,
        invoice_number="INV-STMT-002",
        status=InvoiceStatus.ISSUED,
        issue_date=date.today(),
        subtotal=Decimal("2500.00"),
        total=Decimal("2500.00"),
    )
    db_session.add_all([inv_reg, inv_stmt])
    await db_session.commit()

    # 6. Re-query report: must NOT double-count to $5000; stays faithful to ledger!
    res_after = await client.get("/api/v1/tenant/reports/company-ledger", headers=headers)
    assert res_after.status_code == 200
    data_after = res_after.json()

    assert data_after["summary"]["total_invoiced"] == "2500.00"
    assert data_after["summary"]["total_due"] == "1500.00"


@pytest.mark.asyncio
async def test_company_ledger_dual_sourcing_project_ledger_and_individual_invoices(
    client: AsyncClient, db_session: AsyncSession
):
    """Verifies dual-sourcing architecture:

    - Project finances derived from project ledger (not naive invoice sums).
    - Individual invoices not connected to a project (project_id IS NULL) derived from invoices.
    - Company report summary and timeline accurately unify both.
    """
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session, f"admin-{uuid.uuid4().hex[:6]}@test.com", AdminUserRole.ADMIN, tenant.id
    )
    headers = await _auth_header(admin)

    # 1. Project Alpha + Ledger entries:
    c = Client(
        tenant_id=tenant.id,
        name="Global Dynamics",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)

    p = Project(
        tenant_id=tenant.id,
        name="Turbine Engineering Alpha",
        client_id=c.id,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    # Ledger charge $1500 on project
    ch_p = LedgerEntry(
        project_id=p.id,
        type=LedgerEntryType.CHARGE,
        amount=Decimal("1500.00"),
        description="Turbine Diagnostics",
        source_type=LedgerSourceType.PROJECT_SERVICE,
        entry_date=date.today(),
    )
    # Payment $500 on project
    pay_p = Payment(
        tenant_id=tenant.id,
        client_id=c.id,
        project_id=p.id,
        kind=PaymentKind.RECEIPT,
        amount=Decimal("500.00"),
        method=PaymentMethod.BANK_TRANSFER,
        paid_on=date.today(),
        recorded_by_id=admin.id,
    )
    db_session.add_all([ch_p, pay_p])
    await db_session.commit()

    # 2. Individual / General Invoice (project_id IS NULL) for $600 with $250 paid:
    gen_inv = Invoice(
        tenant_id=tenant.id,
        project_id=None,
        invoice_number="INV-GEN-9001",
        status=InvoiceStatus.PARTIALLY_PAID,
        issue_date=date.today(),
        subtotal=Decimal("600.00"),
        tax_total=Decimal("0.00"),
        total=Decimal("600.00"),
        billed_to={"name": "Independent Contractor Co."},
    )
    db_session.add(gen_inv)
    await db_session.commit()
    await db_session.refresh(gen_inv)

    gen_li = InvoiceLineItem(
        invoice_id=gen_inv.id,
        description="Direct Consultancy Work",
        quantity=Decimal("1.00"),
        unit_price=Decimal("600.00"),
        amount=Decimal("600.00"),
    )
    db_session.add(gen_li)
    await db_session.commit()

    # Record payment transaction of $250 on the individual invoice
    tx_gen = Transaction(
        invoice_id=gen_inv.id,
        amount=Decimal("250.00"),
        direction=TransactionDirection.DEBIT,
        method=PaymentMethod.CASH,
        reference_note="Cash deposit on gen inv",
        recorded_by_id=admin.id,
    )
    db_session.add(tx_gen)
    await db_session.commit()

    # 3. Query Company Ledger report:
    res = await client.get("/api/v1/tenant/reports/company-ledger", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Summary KPI Cards:
    # Invoiced: Project ledger ($1500) + Individual invoice ($600) = $2100.00
    # Collected: Project payment ($500) + Individual invoice payment ($250) = $750.00
    # Due: Project due ($1000) + Individual invoice due ($350) = $1350.00
    summary = data["summary"]
    assert summary["total_invoiced"] == "2100.00"
    assert summary["total_collected"] == "750.00"
    assert summary["total_due"] == "1350.00"

    # Timeline:
    timeline = data["timeline"]
    assert len(timeline) >= 1
    current_period = timeline[0]
    assert current_period["invoiced_amount"] == "2100.00"
    assert current_period["collected_amount"] == "750.00"
    assert current_period["net_due_change"] == "1350.00"

    # Projects Tab:
    projects = data["projects"]
    proj_alpha = next((proj for proj in projects if proj["project_id"] == str(p.id)), None)
    assert proj_alpha is not None
    assert proj_alpha["total_invoiced"] == "1500.00"
    assert proj_alpha["total_paid"] == "500.00"
    assert proj_alpha["balance_due"] == "1000.00"

    # Slicing by project_id excludes general invoices:
    res_proj = await client.get(
        f"/api/v1/tenant/reports/company-ledger?project_id={p.id}", headers=headers
    )
    assert res_proj.status_code == 200
    p_data = res_proj.json()
    assert p_data["summary"]["total_invoiced"] == "1500.00"
    assert p_data["summary"]["total_collected"] == "500.00"
    assert p_data["summary"]["total_due"] == "1000.00"

    # Slicing by client_id excludes general invoices:
    res_client = await client.get(
        f"/api/v1/tenant/reports/company-ledger?client_id={c.id}", headers=headers
    )
    assert res_client.status_code == 200
    c_data = res_client.json()
    assert c_data["summary"]["total_invoiced"] == "1500.00"
    assert c_data["summary"]["total_collected"] == "500.00"
    assert c_data["summary"]["total_due"] == "1000.00"


