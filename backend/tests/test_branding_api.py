"""Integration tests for tenant branding (TODO-011): logo upload + PDF branding."""

from __future__ import annotations

import base64
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import AdminUserRole, ClientStatus, ClientType, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.service import Service
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"

_ONE_PX_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


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
    svc = await _create_service(db_session, tenant.id)
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


# ═══════════════════════════════════════════════════════════════════════════
# Logo upload (TODO-011)
# ═══════════════════════════════════════════════════════════════════════════


class TestBrandingLogoUpload:
    @pytest.mark.asyncio
    async def test_upload_logo_updates_branding(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/branding/logo",
            files={"file": ("logo.png", _ONE_PX_PNG, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["logo_url"].startswith("/uploads/")

        profile = (await client.get("/api/v1/tenant/profile", headers=headers)).json()
        assert profile["logo_url"] == data["logo_url"]
        assert profile["branding"]["logo_url"] == data["logo_url"]

    @pytest.mark.asyncio
    async def test_upload_non_image_rejected(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/branding/logo",
            files={"file": ("logo.txt", b"not an image", "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_unsupported_image_type_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            "/api/v1/tenant/branding/logo",
            files={"file": ("logo.bmp", b"BMfake", "image/bmp")},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_employee_cannot_upload(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, role=AdminUserRole.EMPLOYEE)
        resp = await client.post(
            "/api/v1/tenant/branding/logo",
            files={"file": ("logo.png", _ONE_PX_PNG, "image/png")},
            headers=await _admin_auth_header(ctx["admin"]),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# PDF branding (TODO-011)
# ═══════════════════════════════════════════════════════════════════════════


class TestInvoicePdfBranding:
    @pytest.mark.asyncio
    async def test_pdf_still_renders_with_branding_color_and_logo(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])

        # branding color via profile patch
        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"branding": {"color": "#336699"}},
            headers=headers,
        )
        assert resp.status_code == 200

        # logo upload (writes real file to the uploads dir)
        resp = await client.post(
            "/api/v1/tenant/branding/logo",
            files={"file": ("logo.png", _ONE_PX_PNG, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["logo_url"].startswith("/uploads/")

        # invoice + issue
        inv_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [{"project_service_id": str(ctx["ps"].id)}],
            },
            headers=headers,
        )
        assert inv_resp.status_code == 201
        inv_id = inv_resp.json()["id"]
        issue = await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)
        assert issue.status_code == 200

        # PDF renders despite branding
        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"

    @pytest.mark.asyncio
    async def test_pdf_skips_missing_logo_file(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])

        # branding references a logo file that does not exist on disk
        await client.patch(
            "/api/v1/tenant/profile",
            json={"branding": {"color": "not-a-color", "logo_url": "/uploads/missing.png"}},
            headers=headers,
        )

        inv_resp = await client.post(
            "/api/v1/tenant/invoices/",
            json={
                "project_id": str(ctx["project"].id),
                "line_items": [{"project_service_id": str(ctx["ps"].id)}],
            },
            headers=headers,
        )
        inv_id = inv_resp.json()["id"]
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"
