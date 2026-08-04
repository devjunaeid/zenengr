"""Integration tests for invoice transaction APIs (FEAT-009, TODO-089/090/092/093/094)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.enums import AdminUserRole, ClientStatus, ClientType, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=20,
        max_active_projects=50,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant(
    session: AsyncSession,
    plan_id: uuid.UUID,
    business_name: str = "TestCo",
) -> Tenant:
    tenant = Tenant(
        business_name=business_name,
        slug=f"testco-{uuid.uuid4().hex[:8]}",
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
        full_name=f"Test {role.value}",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=f"Test Client {uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_service(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str = "Test Service",
) -> Service:
    service = Service(
        tenant_id=tenant_id,
        name=f"{name} {uuid.uuid4().hex[:6]}",
        description="",
        default_price="500.00",
        is_active=True,
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service


async def _create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        name=f"Proj {uuid.uuid4().hex[:6]}",
        client_id=client_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def _attach_service(
    session: AsyncSession,
    project_id: uuid.UUID,
    service: Service,
) -> ProjectService:
    ps = ProjectService(
        project_id=project_id,
        service_id=service.id,
        price_at_attachment=service.default_price,
    )
    session.add(ps)
    await session.commit()
    await session.refresh(ps)
    return ps


async def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap(
    db_session: AsyncSession,
    *,
    role: AdminUserRole = AdminUserRole.ADMIN,
):
    """Create plan + tenant + admin + client + service + project + attachment."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session,
        f"admin-{uuid.uuid4().hex[:8]}@testco.com",
        role,
        tenant.id,
    )
    client = await _create_client(db_session, tenant.id)
    svc = await _create_service(db_session, tenant.id, name="Svc")
    project = await _create_project(db_session, tenant.id, client.id)
    ps = await _attach_service(db_session, project.id, svc)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "client": client,
        "svc": svc,
        "project": project,
        "ps": ps,
    }


async def _create_invoice(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
):
    resp = await client.post(
        "/api/v1/tenant/invoices/",
        json={
            "project_id": str(project_id),
            "line_items": [{"project_service_id": str(project_service_id)}],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _issue(client: AsyncClient, headers: dict[str, str], invoice_id: str):
    resp = await client.post(f"/api/v1/tenant/invoices/{invoice_id}/issue", headers=headers)
    assert resp.status_code == 200
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════
# Record transaction
# ═══════════════════════════════════════════════════════════════════════════


class TestRecordTransaction:
    @pytest.mark.asyncio
    async def test_full_payment_marks_paid(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        total = f"{ctx['svc'].default_price:.2f}"
        await _issue(client, headers, inv_id)

        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": total, "method": "bank_transfer"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == total
        assert data["method"] == "bank_transfer"
        assert data["invoice_id"] == inv_id

        detail = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_partial_payment_marks_partially_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        total = Decimal(ctx["svc"].default_price)
        await _issue(client, headers, inv_id)

        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": f"{total / 2:.2f}", "method": "cash"},
            headers=headers,
        )
        assert resp.status_code == 201

        detail = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert detail.json()["status"] == "partially_paid"

    @pytest.mark.asyncio
    async def test_accumulated_partials_mark_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        total = Decimal(ctx["svc"].default_price)
        await _issue(client, headers, inv_id)

        resp1 = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": f"{total * Decimal('0.4'):.2f}", "method": "bank_transfer"},
            headers=headers,
        )
        assert resp1.status_code == 201

        detail = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert detail.json()["status"] == "partially_paid"

        resp2 = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": f"{total * Decimal('0.6'):.2f}", "method": "bank_transfer"},
            headers=headers,
        )
        assert resp2.status_code == 201

        detail = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert detail.json()["status"] == "paid"

    @pytest.mark.asyncio
    async def test_draft_rejects_payment(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        # no issue: stays draft

        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "100.00", "method": "card"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_paid_rejects_payment(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        total = f"{ctx['svc'].default_price:.2f}"
        await _issue(client, headers, inv_id)
        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": total, "method": "bank_transfer"},
            headers=headers,
        )
        assert resp.status_code == 201

        resp2 = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "1.00", "method": "bank_transfer"},
            headers=headers,
        )
        assert resp2.status_code == 422

    @pytest.mark.asyncio
    async def test_employee_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)  # admin creates + issues the invoice
        admin_headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, admin_headers, ctx["project"].id, ctx["ps"].id)
        await _issue(client, admin_headers, inv_id)

        # employee token cannot record payments
        employee = await _create_admin(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            ctx["tenant"].id,
        )
        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "10.00", "method": "cash"},
            headers=await _admin_auth_header(employee),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_auto_allocation_proportional(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [
                    {"description": "A", "unit_price": "200.00"},
                    {"description": "B", "unit_price": "100.00"},
                ],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        inv = resp.json()
        assert inv["total"] == "300.00"
        line_items = inv["line_items"]
        assert [li["description"] for li in line_items] == ["A", "B"]
        await _issue(client, headers, inv["id"])

        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv['id']}/transactions",
            json={"amount": "300.00", "method": "bank_transfer"},
            headers=headers,
        )
        assert resp.status_code == 201

        txs = await client.get(f"/api/v1/tenant/invoices/{inv['id']}/transactions", headers=headers)
        assert txs.status_code == 200
        tx_data = txs.json()
        assert len(tx_data) == 1
        allocations = tx_data[0]["allocations"]
        assert len(allocations) == 2
        by_li = {a["line_item_id"]: a["amount"] for a in allocations}
        assert sum(Decimal(a["amount"]) for a in allocations) == Decimal("300.00")
        assert by_li[line_items[0]["id"]] == "200.00"
        assert by_li[line_items[1]["id"]] == "100.00"

    @pytest.mark.asyncio
    async def test_manual_allocation(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [
                    {"description": "A", "unit_price": "200.00"},
                    {"description": "B", "unit_price": "100.00"},
                ],
            },
            headers=headers,
        )
        inv = resp.json()
        line_items = inv["line_items"]
        inv_id = inv["id"]
        await _issue(client, headers, inv_id)

        # stored as-is
        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={
                "amount": "150.00",
                "method": "cash",
                "allocations": [{"line_item_id": line_items[0]["id"], "amount": "150.00"}],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        allocs = resp.json()["allocations"]
        assert len(allocs) == 1
        assert allocs[0]["line_item_id"] == line_items[0]["id"]
        assert allocs[0]["amount"] == "150.00"

        # wrong-sum allocations -> 422
        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={
                "amount": "150.00",
                "method": "cash",
                "allocations": [{"line_item_id": line_items[0]["id"], "amount": "100.00"}],
            },
            headers=headers,
        )
        assert resp.status_code == 422

        # foreign line_item_id -> 422
        resp = await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={
                "amount": "150.00",
                "method": "cash",
                "allocations": [{"line_item_id": str(uuid.uuid4()), "amount": "150.00"}],
            },
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_transaction_audited(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await _issue(client, headers, inv_id)

        await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "100.00", "method": "other", "reference_note": "ref-1"},
            headers=headers,
        )

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.action == "invoice.payment_recorded",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].entity_type == "transaction"
        assert rows[0].details["invoice_id"] == inv_id
        assert rows[0].details["amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_list_transactions(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await _issue(client, headers, inv_id)

        await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "60.00", "method": "card", "reference_note": "first"},
            headers=headers,
        )
        await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": "40.00", "method": "card", "reference_note": "second"},
            headers=headers,
        )

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/transactions", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert {t["reference_note"] for t in data} == {"first", "second"}
        assert all(len(t["allocations"]) == 1 for t in data)

    @pytest.mark.asyncio
    async def test_record_transaction_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            f"/api/v1/tenant/invoices/{uuid.uuid4()}/transactions",
            json={"amount": "10.00", "method": "cash"},
            headers=headers,
        )
        assert resp.status_code == 404
