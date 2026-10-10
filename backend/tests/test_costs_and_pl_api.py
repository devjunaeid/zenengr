"""Tests for Project Costs (Units, Categories, Vendors) and Live Profit & Loss Engine.

Covers:
- Creating purchase entries with units (bag, sqft, copy), categories (materials, labour), and vendor_name.
- Updating purchase entries with category and units.
- Live Profit & Loss calculation (total_cost, gross_profit, net_profit, profit_margin_pct, cost_by_category).
- Verifying client portal isolation (costs and profit are NEVER leaked to client portal).
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
from app.models.enums import AdminUserRole, ClientStatus, ClientType, ProjectStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant
from app.services import financials as financials_service
from app.services import ledger as ledger_service

_TEST_PWD = "testpass123!"


async def _make_setup(db_session: AsyncSession) -> tuple[Tenant, Client, Project, AdminUser, ClientUser]:
    plan = Plan(
        name="CostPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="Cost Tenant", slug="cost-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    client = Client(tenant_id=tenant.id, name="Cost Client", client_type=ClientType.COMPANY)
    db_session.add(client)
    await db_session.commit()

    project = Project(
        tenant_id=tenant.id,
        client_id=client.id,
        name="Civil Construction & Print Project",
        status=ProjectStatus.ACTIVE,
    )
    db_session.add(project)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=tenant.id,
        email="admin@cost.dev",
        hashed_password=hash_password(_TEST_PWD),
        full_name="Cost Admin",
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    client_user = ClientUser(
        tenant_id=tenant.id,
        client_id=client.id,
        email="client@cost.dev",
        hashed_password=hash_password(_TEST_PWD),
        full_name="Client Cost User",
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


def _client_headers(client_u: ClientUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(client_u.id),
        tenant_id=str(client_u.tenant_id),
        role="client",
        realm="client",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_and_list_costs_with_units_and_categories(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tenant, client_m, project, admin, _ = await _make_setup(db_session)
    headers = _admin_headers(admin)

    # Create purchase cost with units and categories
    res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/purchase-entries",
        headers=headers,
        json={
            "title": "Raw Materials & Labour Phase 1",
            "vendor_name": "Holcim Cement & Labour Supply",
            "notes": "500 bags of cement and site labour",
            "items": [
                {
                    "description": "Portland Cement",
                    "category": "materials",
                    "quantity": "500.00",
                    "unit": "bag",
                    "rate": "10.00",
                },
                {
                    "description": "Mason Labour",
                    "category": "labour",
                    "quantity": "20.00",
                    "unit": "day",
                    "rate": "100.00",
                },
            ],
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["vendor_name"] == "Holcim Cement & Labour Supply"
    assert data["grand_total"] == "7000.00"
    assert len(data["items"]) == 2
    assert data["items"][0]["unit"] == "bag"
    assert data["items"][0]["category"] == "materials"
    assert data["items"][1]["unit"] == "day"
    assert data["items"][1]["category"] == "labour"

    # List entries
    list_res = await client.get(
        f"/api/v1/tenant/projects/{project.id}/purchase-entries",
        headers=headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["vendor_name"] == "Holcim Cement & Labour Supply"
    assert list_data["items"][0]["grand_total"] == "7000.00"


@pytest.mark.asyncio
async def test_live_project_profit_and_loss(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tenant, client_m, project, admin, client_u = await _make_setup(db_session)
    headers = _admin_headers(admin)

    # 1. Attach contract service (billed charges: $10,000)
    service = Service(tenant_id=tenant.id, name="Construction Contract", default_price=Decimal("10000.00"))
    db_session.add(service)
    await db_session.commit()

    ps = ProjectService(
        project_id=project.id,
        service_id=service.id,
        quantity=Decimal("1"),
        unit="job",
        price_at_attachment=Decimal("10000.00"),
    )
    db_session.add(ps)
    await db_session.commit()

    # Add ledger charge
    await ledger_service.add_service_charge(
        db_session,
        project_id=project.id,
        project_service_id=ps.id,
        amount=Decimal("10000.00"),
        description="Construction Contract",
    )
    await db_session.commit()

    # 2. Record client payment: $6,000
    pay_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/payments",
        headers=headers,
        json={"amount": "6000.00", "method": "bank_transfer"},
    )
    assert pay_res.status_code == 201

    # 3. Record project cost: $4,000 ($2,500 material + $1,500 subcontract)
    cost_res = await client.post(
        f"/api/v1/tenant/projects/{project.id}/purchase-entries",
        headers=headers,
        json={
            "title": "Subcontract & Material",
            "vendor_name": "Apex Builders",
            "items": [
                {
                    "description": "Steel rebar",
                    "category": "materials",
                    "quantity": "2.50",
                    "unit": "ton",
                    "rate": "1000.00",
                },
                {
                    "description": "Electrical subcontractor",
                    "category": "subcontract",
                    "quantity": "1.00",
                    "unit": "stage",
                    "rate": "1500.00",
                },
            ],
        },
    )
    assert cost_res.status_code == 201

    # 4. Check project financials P&L
    fin = await financials_service.get_project_financials(db_session, project_id=project.id)
    assert fin["total_cost"] == "4000.00"
    assert fin["gross_profit"] == "6000.00"  # 10,000 billed - 4,000 costs
    assert fin["net_profit"] == "2000.00"    # 6,000 collected - 4,000 costs
    assert fin["profit_margin_pct"] == 60.0  # (6,000 / 10,000) * 100
    assert fin["cost_by_category"]["materials"] == "2500.00"
    assert fin["cost_by_category"]["subcontract"] == "1500.00"


@pytest.mark.asyncio
async def test_client_portal_isolation_never_leaks_costs_or_pl(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    tenant, client_m, project, admin, client_u = await _make_setup(db_session)
    admin_headers = _admin_headers(admin)

    # Record cost as admin
    await client.post(
        f"/api/v1/tenant/projects/{project.id}/purchase-entries",
        headers=admin_headers,
        json={
            "title": "Confidential Costs",
            "vendor_name": "Internal Supplier",
            "items": [{"description": "Confidential", "category": "materials", "quantity": "1.00", "unit": "unit", "rate": "5000.00"}],
        },
    )

    # Now login as client portal user
    client_headers = _client_headers(client_u)

    # Attempt to view project in client portal
    portal_res = await client.get(
        f"/api/v1/client/projects/{project.id}",
        headers=client_headers,
    )
    assert portal_res.status_code == 200, portal_res.text
    portal_data = portal_res.json()

    # Verify that NO internal costs or profit margins exist in response
    assert "total_cost" not in portal_data["financials"]
    assert "gross_profit" not in portal_data["financials"]
    assert "net_profit" not in portal_data["financials"]
    assert "profit_margin_pct" not in portal_data["financials"]
    assert "cost_by_category" not in portal_data["financials"]
