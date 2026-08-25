"""Integration tests for invoice APIs (FEAT-008, TODO-075/076/078/079)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    InvoiceStatus,
    TenantStatus,
)
from app.models.invoice import Invoice
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


# ═══════════════════════════════════════════════════════════════════════════
# Invoice API
# ═══════════════════════════════════════════════════════════════════════════


class TestInvoicesAPI:
    @pytest.mark.asyncio
    async def test_create_draft_with_project_service(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [{"project_service_id": str(ctx["ps"].id)}],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"
        assert data["invoice_number"] is None
        assert data["is_auto"] is False
        assert data["total"] == f"{ctx['svc'].default_price:.2f}"
        assert data["subtotal"] == data["total"]
        assert data["tax_total"] == "0.00"
        assert data["client_id"] == str(ctx["client"].id)
        assert len(data["line_items"]) == 1
        li = data["line_items"][0]
        assert li["description"] == ctx["svc"].name
        assert li["unit_price"] == f"{ctx['svc'].default_price:.2f}"
        assert li["amount"] == f"{ctx['svc'].default_price:.2f}"

    @pytest.mark.asyncio
    async def test_create_draft_with_custom_line_item(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [
                    {"description": "Setup fee", "unit_price": "250.00", "quantity": "2"}
                ],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == "500.00"
        li = data["line_items"][0]
        assert li["amount"] == "500.00"
        assert li["quantity"] == "2.00"
        assert li["project_service_id"] is None
        assert li["entry_date"] == date.today().isoformat()

    @pytest.mark.asyncio
    async def test_create_draft_custom_item_explicit_entry_date(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [
                    {
                        "description": "Setup fee",
                        "unit_price": "250.00",
                        "entry_date": "2026-07-01",
                    }
                ],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == "250.00"
        assert data["line_items"][0]["entry_date"] == "2026-07-01"

    @pytest.mark.asyncio
    async def test_create_draft_validation(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        # empty line items -> 422
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"project_id": str(ctx["project"].id), "line_items": []},
            headers=headers,
        )
        assert resp.status_code == 422
        # random (non-existent) project -> 404
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(uuid.uuid4()),
                "line_items": [{"project_service_id": str(ctx["ps"].id)}],
            },
            headers=headers,
        )
        assert resp.status_code == 404
        # malformed uuid in path -> 404
        resp = await client.get("/api/v1/tenant/invoices/not-a-uuid", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_draft(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={"due_date": "2026-09-30", "notes": "Updated note"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["due_date"] == "2026-09-30"
        assert data["notes"] == "Updated note"

        # Replace line items -> totals recomputed
        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={
                "line_items": [{"description": "Custom", "unit_price": "100.00", "quantity": "3"}]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == "300.00"
        assert len(data["line_items"]) == 1
        assert data["line_items"][0]["description"] == "Custom"
        assert data["line_items"][0]["entry_date"] == date.today().isoformat()

    @pytest.mark.asyncio
    async def test_update_draft_replaced_by_id_keeps_entry_date(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        detail = (await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)).json()
        li_id = detail["line_items"][0]["id"]
        orig_date = detail["line_items"][0]["entry_date"]

        # Replaced by id with entry_date omitted -> original date kept
        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={
                "line_items": [
                    {"id": li_id, "description": "Renamed", "unit_price": "50.00"}
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        li = data["line_items"][0]
        assert li["description"] == "Renamed"
        assert li["entry_date"] == orig_date

        # Replaced by id with explicit entry_date -> input wins
        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={
                "line_items": [
                    {
                        "id": li_id,
                        "description": "Backdated",
                        "unit_price": "50.00",
                        "entry_date": "2026-06-15",
                    }
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["line_items"][0]["entry_date"] == "2026-06-15"

        # New item without id, entry_date omitted -> today
        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={"line_items": [{"description": "New", "unit_price": "10.00"}]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["line_items"][0]["entry_date"] == date.today().isoformat()

    @pytest.mark.asyncio
    async def test_issue_assigns_sequential_number(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv1 = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        inv2 = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        year = date.today().year
        resp1 = await client.post(f"/api/v1/tenant/invoices/{inv1}/issue", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["invoice_number"] == f"INV-{year}-0001"
        assert resp1.json()["status"] == "issued"
        assert resp1.json()["issue_date"] == date.today().isoformat()

        resp2 = await client.post(f"/api/v1/tenant/invoices/{inv2}/issue", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["invoice_number"] == f"INV-{year}-0002"

    @pytest.mark.asyncio
    async def test_issue_non_draft_rejected(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert resp.status_code == 200

        resp2 = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert resp2.status_code == 422

    @pytest.mark.asyncio
    async def test_issue_not_found(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            f"/api/v1/tenant/invoices/{uuid.uuid4()}/issue",
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_patch_issued_locked(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        # due_date locked after issue
        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={"due_date": "2026-12-01"},
            headers=headers,
        )
        assert resp.status_code == 422

        # notes still editable after issue
        resp = await client.patch(
            f"/api/v1/tenant/invoices/{inv_id}",
            json={"notes": "Post-issue note"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Post-issue note"

    @pytest.mark.asyncio
    async def test_delete_draft(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        resp = await client.delete(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_issued_rejected(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.delete(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_employee_cannot_create(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, role=AdminUserRole.EMPLOYEE)
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [{"project_service_id": str(ctx["ps"].id)}],
            },
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_invoices(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv1 = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        inv2 = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        resp = await client.get("/api/v1/tenant/invoices/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert {item["id"] for item in data["items"]} == {inv1, inv2}

        # status filter works
        resp = await client.get("/api/v1/tenant/invoices/?status=draft", headers=headers)
        assert resp.json()["total"] == 2
        await client.post(f"/api/v1/tenant/invoices/{inv1}/issue", headers=headers)
        resp = await client.get("/api/v1/tenant/invoices/?status=issued", headers=headers)
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_invoices_filter_by_client(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        # second client + project + attachment
        client_b = await _create_client(db_session, ctx["tenant"].id)
        project_b = await _create_project(db_session, ctx["tenant"].id, client_b.id)
        ps_b = await _attach_service(db_session, project_b.id, ctx["svc"])
        inv_a = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        inv_b = await _create_invoice(client, headers, project_b.id, ps_b.id)
        # general (project-less) invoice
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"line_items": [{"description": "Internal", "unit_price": "50.00"}]},
            headers=headers,
        )
        assert resp.status_code == 201
        gen_id = resp.json()["id"]

        # client A filter -> only client A's project invoice, general excluded
        resp = await client.get(
            f"/api/v1/tenant/invoices/?client_id={ctx['client'].id}", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert [item["id"] for item in data["items"]] == [inv_a]

        # client B filter -> only client B's project invoice
        resp = await client.get(
            f"/api/v1/tenant/invoices/?client_id={client_b.id}", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert [item["id"] for item in data["items"]] == [inv_b]

        # invalid uuid -> 422
        resp = await client.get(
            "/api/v1/tenant/invoices/?client_id=not-a-uuid", headers=headers
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "client_id must be a valid UUID"

        # no client_id -> all three invoices
        resp = await client.get("/api/v1/tenant/invoices/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert {item["id"] for item in data["items"]} == {inv_a, inv_b, gen_id}


# ═══════════════════════════════════════════════════════════════════════════
# Void invoice (TODO-081)
# ═══════════════════════════════════════════════════════════════════════════


class TestVoidInvoice:
    @pytest.mark.asyncio
    async def test_void_issued_invoice(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert resp.status_code == 200
        issued_number = resp.json()["invoice_number"]
        assert issued_number is not None

        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "void"
        assert data["invoice_number"] == issued_number  # number retained
        assert data["total"] == f"{ctx['svc'].default_price:.2f}"

        # detail also shows void
        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "void"

    @pytest.mark.asyncio
    async def test_void_draft_and_already_void_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        # draft -> 422 (drafts are deleted, not voided)
        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=headers)
        assert resp.status_code == 422
        assert "Only issued" in resp.json()["error"]["message"]

        # already void -> 422
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=headers)
        assert resp.status_code == 200
        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=headers)
        assert resp.status_code == 422
        assert "already voided" in resp.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_void_audited(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=headers)

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.action == "invoice.voided",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].entity_type == "invoice"
        assert rows[0].entity_id == inv_id
        assert rows[0].details["invoice_number"].startswith("INV-")

    @pytest.mark.asyncio
    async def test_void_not_found(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            f"/api/v1/tenant/invoices/{uuid.uuid4()}/void",
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Invoice PDF (TODO-084/085)
# ═══════════════════════════════════════════════════════════════════════════


class TestInvoicePDF:
    @pytest.mark.asyncio
    async def test_issued_invoice_pdf(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"
        disposition = resp.headers["content-disposition"]
        assert "filename=" in disposition
        assert disposition.startswith("attachment;")

    @pytest.mark.asyncio
    async def test_draft_invoice_pdf_uses_draft_filename(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"
        assert 'filename="DRAFT.pdf"' in resp.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_paid_invoice_pdf_renders_successfully(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        # Record a payment
        await client.post(
            f"/api/v1/tenant/invoices/{inv_id}/transactions",
            json={"amount": 50.00, "method": "bank_transfer", "reference_note": "Deposit"},
            headers=headers,
        )

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_pdf_not_found(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await client.get(
            f"/api/v1/tenant/invoices/{uuid.uuid4()}/pdf",
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# General (internal) invoices (FEAT-015, TODO-152/153)
# ═══════════════════════════════════════════════════════════════════════════


class TestGeneralInvoice:
    @pytest.mark.asyncio
    async def test_create_general_invoice_with_custom_line_items(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "line_items": [
                    {"description": "Internal consulting", "unit_price": "750.00", "quantity": "2"}
                ]
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "draft"
        assert data["invoice_number"] is None
        assert data["project_id"] is None
        assert data["client_id"] is None
        assert data["is_general"] is True
        assert data["is_auto"] is False
        assert data["total"] == "1500.00"
        assert len(data["line_items"]) == 1
        li = data["line_items"][0]
        assert li["description"] == "Internal consulting"
        assert li["amount"] == "1500.00"
        assert li["project_service_id"] is None

    @pytest.mark.asyncio
    async def test_general_invoice_rejects_project_service_line_item(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"line_items": [{"project_service_id": str(ctx["ps"].id)}]},
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["message"] == "Project service line items require a project"

    @pytest.mark.asyncio
    async def test_project_invoice_with_custom_items_still_works(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [{"description": "Custom", "unit_price": "100.00", "quantity": "1"}],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["project_id"] == str(ctx["project"].id)
        assert data["client_id"] == str(ctx["client"].id)
        assert data["is_general"] is False
        assert data["total"] == "100.00"

    @pytest.mark.asyncio
    async def test_issue_general_invoice_shares_sequence(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        # project invoice issued first -> 0001
        proj_inv = await _create_invoice(client, headers, ctx["project"].id, ctx["ps"].id)
        await client.post(f"/api/v1/tenant/invoices/{proj_inv}/issue", headers=headers)

        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"line_items": [{"description": "Internal", "unit_price": "50.00"}]},
            headers=headers,
        )
        assert resp.status_code == 201
        gen_id = resp.json()["id"]

        year = date.today().year
        resp = await client.post(f"/api/v1/tenant/invoices/{gen_id}/issue", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_number"] == f"INV-{year}-0002"
        assert data["status"] == "issued"
        assert data["project_id"] is None
        assert data["client_id"] is None
        assert data["is_general"] is True

    @pytest.mark.asyncio
    async def test_general_invoice_list_detail_and_void(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"line_items": [{"description": "Internal", "unit_price": "50.00"}]},
            headers=headers,
        )
        assert resp.status_code == 201
        gen_id = resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{gen_id}/issue", headers=headers)

        # list renders general invoice with null project/client
        resp = await client.get("/api/v1/tenant/invoices/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["id"] == gen_id
        assert item["project_id"] is None
        assert item["client_id"] is None
        assert item["status"] == "issued"
        assert item["is_auto"] is False

        # detail renders without crashing
        resp = await client.get(f"/api/v1/tenant/invoices/{gen_id}", headers=headers)
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["project_id"] is None
        assert detail["client_id"] is None
        assert detail["is_general"] is True
        assert len(detail["line_items"]) == 1

        # void works
        resp = await client.post(f"/api/v1/tenant/invoices/{gen_id}/void", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "void"

    @pytest.mark.asyncio
    async def test_general_invoice_pdf(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={"line_items": [{"description": "Internal", "unit_price": "50.00"}]},
            headers=headers,
        )
        assert resp.status_code == 201
        gen_id = resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{gen_id}/issue", headers=headers)

        resp = await client.get(f"/api/v1/tenant/invoices/{gen_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")


# ═══════════════════════════════════════════════════════════════════════════
# Auto (statement) invoices: cannot be issued, deleted, or voided
# ═══════════════════════════════════════════════════════════════════════════


async def _create_auto_statement(
    client: AsyncClient,
    headers: dict[str, str],
    db_session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    service_id: uuid.UUID,
) -> str:
    """Create a project with auto_invoice on; return the auto draft invoice id."""
    resp = await client.post(
        "/api/v1/tenant/projects/",
        json={
            "name": f"AutoStmt-{uuid.uuid4().hex[:6]}",
            "client_id": str(client_id),
            "service_ids": [str(service_id)],
            "auto_invoice": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    pid = resp.json()["id"]

    inv = (
        await db_session.execute(
            select(Invoice).where(Invoice.project_id == pid, Invoice.is_auto.is_(True))
        )
    ).scalar_one()
    assert inv.status == InvoiceStatus.DRAFT
    return str(inv.id)


class TestAutoStatementInvoice:
    @pytest.mark.asyncio
    async def test_issue_auto_statement_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_auto_statement(
            client,
            headers,
            db_session,
            tenant_id=ctx["tenant"].id,
            client_id=ctx["client"].id,
            service_id=ctx["svc"].id,
        )

        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert resp.status_code == 422
        assert "cannot be issued" in resp.json()["error"]["message"]

        # still a draft afterwards
        detail = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["status"] == "draft"
        assert detail.json()["is_auto"] is True

    @pytest.mark.asyncio
    async def test_delete_auto_statement_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_auto_statement(
            client,
            headers,
            db_session,
            tenant_id=ctx["tenant"].id,
            client_id=ctx["client"].id,
            service_id=ctx["svc"].id,
        )

        resp = await client.delete(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert resp.status_code == 405
        assert "cannot be deleted" in resp.json()["error"]["message"]

        # still exists
        detail = await client.get(f"/api/v1/tenant/invoices/{inv_id}", headers=headers)
        assert detail.status_code == 200

    @pytest.mark.asyncio
    async def test_void_auto_statement_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        inv_id = await _create_auto_statement(
            client,
            headers,
            db_session,
            tenant_id=ctx["tenant"].id,
            client_id=ctx["client"].id,
            service_id=ctx["svc"].id,
        )

        resp = await client.post(f"/api/v1/tenant/invoices/{inv_id}/void", headers=headers)
        assert resp.status_code == 422
        assert "cannot be voided" in resp.json()["error"]["message"]
