"""Integration tests for client-portal data endpoints (TODO-081).

Covers: client invoice list/detail (paid/balance), leak prevention between
clients, void invoices hidden from the portal list, and client project
list/detail with milestones + financial rollups.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.client_user import ClientUser
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    InvoiceStatus,
    MilestoneStatus,
    TenantStatus,
)
from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
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


async def _create_tenant(session: AsyncSession, plan_id: uuid.UUID) -> Tenant:
    tenant = Tenant(
        business_name="TestCo",
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_admin(session: AsyncSession, tenant_id: uuid.UUID) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=f"admin-{uuid.uuid4().hex[:8]}@testco.com",
        full_name="Test Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.ADMIN,
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


async def _create_client_user(
    session: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=f"cu-{uuid.uuid4().hex[:8]}@client.com",
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=True,
    )
    session.add(cu)
    await session.commit()
    await session.refresh(cu)
    return cu


async def _create_service(session: AsyncSession, tenant_id: uuid.UUID) -> Service:
    service = Service(
        tenant_id=tenant_id,
        name=f"Svc {uuid.uuid4().hex[:6]}",
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
        client_id=client_id,
        name=f"Proj {uuid.uuid4().hex[:6]}",
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


async def _add_milestone(
    session: AsyncSession,
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
    service_id: uuid.UUID,
    *,
    sequence_order: int,
    status: MilestoneStatus = MilestoneStatus.PENDING,
) -> ProjectMilestone:
    m = ProjectMilestone(
        project_id=project_id,
        project_service_id=project_service_id,
        service_id=service_id,
        name=f"M{sequence_order}",
        sequence_order=sequence_order,
        status=status,
    )
    session.add(m)
    await session.commit()
    await session.refresh(m)
    return m


async def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _client_auth_header(user: ClientUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role="client_user",
        realm="client",
        client_id=str(user.client_id),
    )
    return {"Authorization": f"Bearer {token}"}


async def _bootstrap(db_session: AsyncSession):
    """Plan + tenant + admin + two clients (A, B) with client users + service."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(db_session, tenant.id)
    client_a = await _create_client(db_session, tenant.id)
    client_b = await _create_client(db_session, tenant.id)
    cu_a = await _create_client_user(db_session, client_a.id, tenant.id)
    cu_b = await _create_client_user(db_session, client_b.id, tenant.id)
    svc = await _create_service(db_session, tenant.id)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "client_a": client_a,
        "client_b": client_b,
        "cu_a": cu_a,
        "cu_b": cu_b,
        "svc": svc,
    }


async def _create_and_issue_invoice(
    client: AsyncClient,
    headers: dict[str, str],
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
) -> str:
    resp = await client.post(
        "/api/v1/tenant/invoices/",
        json={
            "project_id": str(project_id),
            "line_items": [{"project_service_id": str(project_service_id)}],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    inv_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
    assert resp.status_code == 200
    return inv_id


async def _record_transaction(
    client: AsyncClient,
    headers: dict[str, str],
    invoice_id: str,
    amount: str,
) -> None:
    resp = await client.post(
        f"/api/v1/tenant/invoices/{invoice_id}/transactions",
        json={"amount": amount, "method": "bank_transfer"},
        headers=headers,
    )
    assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════
# Client invoice portal
# ═══════════════════════════════════════════════════════════════════════════


class TestClientInvoicePortal:
    @pytest.mark.asyncio
    async def test_client_lists_own_invoices(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 20
        item = data["items"][0]
        assert item["id"] == inv_id
        assert item["status"] == "issued"
        assert item["project_id"] == str(proj.id)
        assert item["project_name"] == proj.name
        assert item["total"] == f"{ctx['svc'].default_price:.2f}"
        assert item["invoice_number"].startswith("INV-")

        # client B sees nothing
        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_client_invoice_detail_paid_and_balance(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        await _record_transaction(client, admin_headers, inv_id, "200.00")

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "partially_paid"
        assert data["project_name"] == proj.name
        assert data["subtotal"] == "500.00"
        assert data["tax_total"] == "0.00"
        assert data["total"] == "500.00"
        assert data["paid_amount"] == "200.00"
        assert data["balance_due"] == "300.00"
        assert len(data["line_items"]) == 1
        li = data["line_items"][0]
        assert li["amount"] == "500.00"
        assert li["project_service_id"] == str(ps.id)

        # full payment -> balance clamped to 0.00
        await _record_transaction(client, admin_headers, inv_id, "300.00")
        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.json()["paid_amount"] == "500.00"
        assert resp.json()["balance_due"] == "0.00"

    @pytest.mark.asyncio
    async def test_client_cannot_see_other_clients_invoice(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}",
            headers=await _client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_invoice_invalid_status_filter_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            "/api/v1/client/invoices/?status=bogus",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_client_list_excludes_void_invoices(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=admin_headers)
        assert resp.status_code == 200

        # hidden from client portal list
        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

        # still visible in the tenant ledger
        resp = await client.get("/api/v1/tenant/invoices/?status=void", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_client_invoice_invalid_uuid_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            "/api/v1/client/invoices/not-a-uuid",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Client project portal
# ═══════════════════════════════════════════════════════════════════════════


class TestClientProjectPortal:
    @pytest.mark.asyncio
    async def test_client_lists_own_projects_with_completion(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        await _add_milestone(
            db_session,
            proj.id,
            ps.id,
            ctx["svc"].id,
            sequence_order=1,
            status=MilestoneStatus.COMPLETED,
        )
        await _add_milestone(db_session, proj.id, ps.id, ctx["svc"].id, sequence_order=2)
        # a project for the other client must not leak
        await _create_project(db_session, ctx["tenant"].id, ctx["client_b"].id)

        resp = await client.get(
            "/api/v1/client/projects/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["id"] == str(proj.id)
        assert item["name"] == proj.name
        assert item["status"] == "draft"
        assert item["milestone_total"] == 2
        assert item["milestone_completed"] == 1
        assert item["milestone_completion_pct"] == 50.0
        assert item["start_date"] is None

    @pytest.mark.asyncio
    async def test_client_project_detail_services_milestones_financials(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        await _add_milestone(
            db_session,
            proj.id,
            ps.id,
            ctx["svc"].id,
            sequence_order=1,
            status=MilestoneStatus.COMPLETED,
        )
        await _add_milestone(db_session, proj.id, ps.id, ctx["svc"].id, sequence_order=2)
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        await _record_transaction(client, admin_headers, inv_id, "200.00")

        resp = await client.get(
            f"/api/v1/client/projects/{proj.id}",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(proj.id)
        assert data["client_id"] == str(ctx["client_a"].id)
        assert data["milestone_total"] == 2
        assert data["milestone_completed"] == 1
        assert data["milestone_completion_pct"] == 50.0

        assert len(data["services"]) == 1
        svc_item = data["services"][0]
        assert svc_item["id"] == str(ps.id)
        assert svc_item["service_name"] == ctx["svc"].name
        assert svc_item["status"] == "active"
        assert svc_item["price_at_attachment"] == "500.00"

        assert len(data["milestones"]) == 2
        m_item = data["milestones"][0]
        assert m_item["name"] == "M1"
        assert m_item["sequence_order"] == 1
        assert m_item["status"] == "completed"

        assert data["financials"] == {
            "total_invoiced": "500.00",
            "total_paid": "200.00",
            "balance_due": "300.00",
        }
        assert len(data["linked_invoices"]) == 1
        li = data["linked_invoices"][0]
        assert li["id"] == inv_id
        assert li["number"].startswith("INV-")
        assert li["status"] == "partially_paid"
        assert li["total"] == "500.00"

    @pytest.mark.asyncio
    async def test_client_project_detail_other_client_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)

        resp = await client.get(
            f"/api/v1/client/projects/{proj.id}",
            headers=await _client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_project_invalid_status_filter_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            "/api/v1/client/projects/?status=bogus",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_client_project_invalid_uuid_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            "/api/v1/client/projects/not-a-uuid",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Client formatting settings (FEAT-014, TODO-147)
# ═══════════════════════════════════════════════════════════════════════════


class TestClientFormattingSettings:
    @pytest.mark.asyncio
    async def test_client_settings_returns_defaults_for_fresh_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            "/api/v1/client/settings",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "currency": "USD",
            "timezone": "UTC",
            "date_format": "YYYY-MM-DD",
            "time_format": "24h",
        }

    @pytest.mark.asyncio
    async def test_client_settings_reflects_tenant_override(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])

        resp = await client.patch(
            "/api/v1/tenant/settings/date_format",
            json={"value": "DD/MM/YYYY"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

        resp = await client.get(
            "/api/v1/client/settings",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["date_format"] == "DD/MM/YYYY"
        # untouched keys still resolve to defaults
        assert data["currency"] == "USD"
        assert data["timezone"] == "UTC"
        assert data["time_format"] == "24h"

    @pytest.mark.asyncio
    async def test_admin_token_rejected_on_client_settings(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            "/api/v1/client/settings",
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# Client invoice PDF (TODO-084/085)
# ═══════════════════════════════════════════════════════════════════════════


class TestClientInvoicePDF:
    @pytest.mark.asyncio
    async def test_client_downloads_own_invoice_pdf(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}/pdf",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"
        disposition = resp.headers["content-disposition"]
        assert "filename=" in disposition
        assert disposition.startswith("attachment;")

    @pytest.mark.asyncio
    async def test_client_pdf_other_clients_invoice_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}/pdf",
            headers=await _client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Client detail financial rollup (TODO-097 backend part)
# ═══════════════════════════════════════════════════════════════════════════


class TestClientDetailFinancials:
    @pytest.mark.asyncio
    async def test_client_detail_live_financials(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/tenant/clients/{ctx['client_a'].id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoiced"] == "500.00"
        assert data["total_paid"] == "0.00"
        assert data["total_outstanding"] == "500.00"

        # after a payment, outstanding drops
        await _record_transaction(client, admin_headers, inv_id, "200.00")
        resp = await client.get(
            f"/api/v1/tenant/clients/{ctx['client_a'].id}",
            headers=admin_headers,
        )
        data = resp.json()
        assert data["total_invoiced"] == "500.00"
        assert data["total_paid"] == "200.00"
        assert data["total_outstanding"] == "300.00"

    @pytest.mark.asyncio
    async def test_client_detail_zeroed_for_untouched_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/tenant/clients/{ctx['client_b'].id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoiced"] == "0.00"
        assert data["total_paid"] == "0.00"
        assert data["total_outstanding"] == "0.00"


# ═══════════════════════════════════════════════════════════════════════════
# Client invoice transactions (TODO-098 backend part)
# ═══════════════════════════════════════════════════════════════════════════


class TestClientInvoiceTransactions:
    @pytest.mark.asyncio
    async def test_client_lists_own_invoice_transactions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        await _record_transaction(client, admin_headers, inv_id, "200.00")

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}/transactions",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        tx = data[0]
        assert tx["invoice_id"] == inv_id
        assert tx["amount"] == "200.00"
        assert tx["method"] == "bank_transfer"
        assert tx["reference_note"] == ""
        assert tx["recorded_by_id"] == str(ctx["admin"].id)
        assert tx["recorded_at"]
        assert len(tx["allocations"]) == 1
        alloc = tx["allocations"][0]
        assert alloc["line_item_id"]
        assert alloc["amount"] == "200.00"

    @pytest.mark.asyncio
    async def test_client_transactions_other_clients_invoice_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}/transactions",
            headers=await _client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_transactions_empty_invoice_returns_empty_list(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)

        resp = await client.get(
            f"/api/v1/client/invoices/{inv_id}/transactions",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════════
# General invoices excluded from portal + rollups (FEAT-015, TODO-152/153)
# ═══════════════════════════════════════════════════════════════════════════


class TestGeneralInvoicePortalExclusion:
    @pytest.mark.asyncio
    async def test_general_invoice_hidden_from_client_portal_and_financials(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])

        # create + issue a general (internal) invoice with no project/client
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"line_items": [{"description": "Internal", "unit_price": "1000.00"}]},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        gen_id = resp.json()["id"]
        resp = await client.post(f"/api/v1/tenant/invoices/{gen_id}/issue", headers=admin_headers)
        assert resp.status_code == 200

        # client portal list excludes the general invoice
        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

        # client financial rollup unchanged by the general invoice
        resp = await client.get(
            f"/api/v1/tenant/clients/{ctx['client_a'].id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoiced"] == "0.00"
        assert data["total_paid"] == "0.00"
        assert data["total_outstanding"] == "0.00"

        # client project financial rollup + linked invoices unchanged
        resp = await client.get(
            f"/api/v1/client/projects/{proj.id}",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["financials"] == {
            "total_invoiced": "0.00",
            "total_paid": "0.00",
            "balance_due": "0.00",
        }
        assert data["linked_invoices"] == []

        # control: a normal project invoice does show up
        inv_id = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["id"] == inv_id


# ═══════════════════════════════════════════════════════════════════════════
# Client ledger (FEAT-015, TODO-158)
# ═══════════════════════════════════════════════════════════════════════════


class TestClientLedger:
    @pytest.mark.asyncio
    async def test_staff_and_client_ledger_after_pay_overpay_refund_apply(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv1 = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        await _record_transaction(client, admin_headers, inv1, "600.00")  # overpay -> advance 100
        refund = await client.post(
            f"/api/v1/tenant/invoices/{inv1}/refund",
            json={"amount": "200.00"},
            headers=admin_headers,
        )
        assert refund.status_code == 201

        inv2_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(proj.id),
                "line_items": [{"description": "Custom", "unit_price": "300.00"}],
            },
            headers=admin_headers,
        )
        assert inv2_resp.status_code == 201
        inv2 = inv2_resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv2}/issue", headers=admin_headers)
        applied = await client.post(
            f"/api/v1/tenant/invoices/{inv2}/apply-advance",
            json={},
            headers=admin_headers,
        )
        assert applied.status_code == 200

        expected_entries = [
            {"kind": "payment", "amount": "600.00", "running_balance": "600.00"},
            {"kind": "advance_received", "amount": "-100.00", "running_balance": "500.00"},
            {"kind": "refund", "amount": "-200.00", "running_balance": "300.00"},
            {"kind": "advance_applied", "amount": "100.00", "running_balance": "400.00"},
        ]

        resp = await client.get(
            f"/api/v1/tenant/clients/{ctx['client_a'].id}/ledger",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["advance_balance"] == "0.00"
        assert len(data["entries"]) == 4
        for entry, expected in zip(data["entries"], expected_entries, strict=True):
            assert entry["kind"] == expected["kind"]
            assert entry["amount"] == expected["amount"]
            assert entry["running_balance"] == expected["running_balance"]
            assert entry["id"]
            assert entry["created_at"]

        # client portal sees the same ledger for their own client
        resp = await client.get(
            "/api/v1/client/ledger",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json() == data

    @pytest.mark.asyncio
    async def test_client_ledger_scoped_to_own_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        proj = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        ps = await _attach_service(db_session, proj.id, ctx["svc"])
        inv1 = await _create_and_issue_invoice(client, admin_headers, proj.id, ps.id)
        await _record_transaction(client, admin_headers, inv1, "600.00")

        # client B's ledger is empty (no data isolation leak)
        resp = await client.get(
            "/api/v1/client/ledger",
            headers=await _client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 200
        assert resp.json() == {"advance_balance": "0.00", "entries": []}

    @pytest.mark.asyncio
    async def test_staff_ledger_unknown_client_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        resp = await client.get(
            f"/api/v1/tenant/clients/{uuid.uuid4()}/ledger",
            headers=admin_headers,
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Auto (statement) invoices excluded from client portal (is_auto)
# ═══════════════════════════════════════════════════════════════════════════


class TestAutoInvoicePortalExclusion:
    @pytest.mark.asyncio
    async def test_auto_invoice_staff_only_manual_invoice_client_visible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])

        # project with auto_invoice on: creating it with services makes an
        # auto draft (statement)
        proj = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "AutoStmt",
                    "client_id": str(ctx["client_a"].id),
                    "service_ids": [str(ctx["svc"].id)],
                    "auto_invoice": True,
                },
                headers=admin_headers,
            )
        ).json()["id"]

        auto_draft = (
            await db_session.execute(
                select(Invoice).where(
                    Invoice.project_id == proj, Invoice.status == InvoiceStatus.DRAFT
                )
            )
        ).scalar_one()
        assert auto_draft.is_auto is True

        # issue the auto draft: flag survives
        resp = await client.post(
            f"/api/v1/tenant/invoices/{auto_draft.id}/issue",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "issued"
        assert data["is_auto"] is True

        # client portal list does not include the issued auto invoice
        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

        # client portal detail 404s for the auto invoice
        resp = await client.get(
            f"/api/v1/client/invoices/{auto_draft.id}",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404

        # manual invoice on the same project: is_auto False, client-visible
        proj_detail = (
            await client.get(f"/api/v1/tenant/projects/{proj}", headers=admin_headers)
        ).json()
        ps_id = proj_detail["services"][0]["id"]
        manual_id = await _create_and_issue_invoice(client, admin_headers, proj, ps_id)

        resp = await client.get(
            f"/api/v1/tenant/invoices/{manual_id}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_auto"] is False

        resp = await client.get(
            "/api/v1/client/invoices/",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == manual_id

        # client project detail linked_invoices excludes the auto statement
        resp = await client.get(
            f"/api/v1/client/projects/{proj}",
            headers=await _client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert [li["id"] for li in data["linked_invoices"]] == [manual_id]

        # staff project overview includes both (exclude_auto defaults to False)
        resp = await client.get(
            f"/api/v1/tenant/projects/{proj}/overview",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert {li["id"] for li in data["linked_invoices"]} == {
            str(auto_draft.id),
            manual_id,
        }

    @pytest.mark.asyncio
    async def test_auto_invoice_pdf_and_transactions_hidden_from_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])

        # project with auto_invoice on: creating it with services makes an
        # auto draft (statement)
        proj = (
            await client.post(
                "/api/v1/tenant/projects/",
                json={
                    "name": "AutoStmtPdfTx",
                    "client_id": str(ctx["client_a"].id),
                    "service_ids": [str(ctx["svc"].id)],
                    "auto_invoice": True,
                },
                headers=admin_headers,
            )
        ).json()["id"]

        auto_draft = (
            await db_session.execute(
                select(Invoice).where(
                    Invoice.project_id == proj, Invoice.status == InvoiceStatus.DRAFT
                )
            )
        ).scalar_one()
        assert auto_draft.is_auto is True

        # issue the auto draft and record a payment against it
        resp = await client.post(
            f"/api/v1/tenant/invoices/{auto_draft.id}/issue",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        await _record_transaction(client, admin_headers, str(auto_draft.id), "100.00")

        # manual invoice on the same project: is_auto False, client-visible
        proj_detail = (
            await client.get(f"/api/v1/tenant/projects/{proj}", headers=admin_headers)
        ).json()
        ps_id = proj_detail["services"][0]["id"]
        manual_id = await _create_and_issue_invoice(client, admin_headers, proj, ps_id)
        await _record_transaction(client, admin_headers, manual_id, "100.00")

        cu_headers = await _client_auth_header(ctx["cu_a"])

        # client PDF: auto invoice 404s (even with payment history), manual 200
        resp = await client.get(
            f"/api/v1/client/invoices/{auto_draft.id}/pdf",
            headers=cu_headers,
        )
        assert resp.status_code == 404

        resp = await client.get(
            f"/api/v1/client/invoices/{manual_id}/pdf",
            headers=cu_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"

        # client transactions: auto invoice 404s, manual still lists payments
        resp = await client.get(
            f"/api/v1/client/invoices/{auto_draft.id}/transactions",
            headers=cu_headers,
        )
        assert resp.status_code == 404

        resp = await client.get(
            f"/api/v1/client/invoices/{manual_id}/transactions",
            headers=cu_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["amount"] == "100.00"
        assert data[0]["invoice_id"] == manual_id
