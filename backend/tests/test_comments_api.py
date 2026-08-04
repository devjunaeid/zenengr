"""Integration tests for project comment APIs (FEAT-010, TODO-100/103/104/106/107)."""

from __future__ import annotations

import logging
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_user import ClientUser
from app.models.enums import AdminUserRole, ClientStatus, ClientType, TenantStatus
from app.models.plan import Plan
from app.models.project import Project
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


async def _create_admin(
    session: AsyncSession,
    email: str,
    role: AdminUserRole,
    tenant_id: uuid.UUID,
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


async def _create_client_user(
    session: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID,
    email: str,
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=email,
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=True,
    )
    session.add(cu)
    await session.commit()
    await session.refresh(cu)
    return cu


async def _create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    *,
    owner_id: uuid.UUID | None = None,
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        client_id=client_id,
        name=f"Proj {uuid.uuid4().hex[:6]}",
        owner_id=owner_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


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
    """Plan + tenant + admin (ADMIN) + employee + client + client_user + project."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session,
        f"admin-{uuid.uuid4().hex[:8]}@testco.com",
        AdminUserRole.ADMIN,
        tenant.id,
    )
    employee = await _create_admin(
        db_session,
        f"emp-{uuid.uuid4().hex[:8]}@testco.com",
        AdminUserRole.EMPLOYEE,
        tenant.id,
    )
    client = await _create_client(db_session, tenant.id)
    client_user = await _create_client_user(
        db_session,
        client.id,
        tenant.id,
        f"cu-{uuid.uuid4().hex[:8]}@client.com",
    )
    project = await _create_project(db_session, tenant.id, client.id, owner_id=admin.id)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "employee": employee,
        "client": client,
        "client_user": client_user,
        "project": project,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Tenant comments
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantComments:
    @pytest.mark.asyncio
    async def test_admin_posts_comment(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "hello"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["author_type"] == "tenant_admin"
        assert data["author_name"] == ctx["admin"].full_name
        assert data["is_internal"] is False
        assert data["project_id"] == str(ctx["project"].id)

    @pytest.mark.asyncio
    async def test_internal_comment_flag(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "internal note", "is_internal": True},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["is_internal"] is True

    @pytest.mark.asyncio
    async def test_employee_owner_posts(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        emp_project = await _create_project(
            db_session,
            ctx["tenant"].id,
            ctx["client"].id,
            owner_id=ctx["employee"].id,
        )
        resp = await client.post(
            f"/api/v1/tenant/projects/{emp_project.id}/comments",
            json={"content": "mine"},
            headers=await _admin_auth_header(ctx["employee"]),
        )
        assert resp.status_code == 201
        assert resp.json()["author_type"] == "tenant_employee"

    @pytest.mark.asyncio
    async def test_employee_non_owner_forbidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "nope"},
            headers=await _admin_auth_header(ctx["employee"]),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_content_422(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": ""},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_returns_all(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        url = f"/api/v1/tenant/projects/{ctx['project'].id}/comments"
        await client.post(url, json={"content": "shared"}, headers=headers)
        await client.post(
            url,
            json={"content": "internal", "is_internal": True},
            headers=headers,
        )

        resp = await client.get(url, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        by_content = {c["content"]: c for c in data}
        assert by_content["shared"]["is_internal"] is False
        assert by_content["internal"]["is_internal"] is True

    @pytest.mark.asyncio
    async def test_comment_audited(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "audit me"},
            headers=headers,
        )

        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.action == "comment.created",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].entity_type == "comment"
        assert rows[0].details["project_id"] == str(ctx["project"].id)


# ═══════════════════════════════════════════════════════════════════════════
# Client comments
# ═══════════════════════════════════════════════════════════════════════════


class TestClientComments:
    @pytest.mark.asyncio
    async def test_client_posts_shared(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _client_auth_header(ctx["client_user"])
        resp = await client.post(
            f"/api/v1/client/projects/{ctx['project'].id}/comments",
            json={"content": "client msg", "is_internal": True},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_internal"] is False  # forced server-side
        assert data["author_type"] == "client_user"
        assert data["author_name"] == "Test Client User"

    @pytest.mark.asyncio
    async def test_client_gets_shared_only(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        admin_headers = await _admin_auth_header(ctx["admin"])
        tenant_url = f"/api/v1/tenant/projects/{ctx['project'].id}/comments"
        await client.post(tenant_url, json={"content": "shared"}, headers=admin_headers)
        await client.post(
            tenant_url,
            json={"content": "internal", "is_internal": True},
            headers=admin_headers,
        )

        resp = await client.get(
            f"/api/v1/client/projects/{ctx['project'].id}/comments",
            headers=await _client_auth_header(ctx["client_user"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["content"] == "shared"
        assert data[0]["is_internal"] is False

    @pytest.mark.asyncio
    async def test_client_cannot_access_other_client_project(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        other_client = await _create_client(db_session, ctx["tenant"].id)
        other_cu = await _create_client_user(
            db_session,
            other_client.id,
            ctx["tenant"].id,
            f"ocu-{uuid.uuid4().hex[:8]}@client.com",
        )
        headers = await _client_auth_header(other_cu)
        url = f"/api/v1/client/projects/{ctx['project'].id}/comments"

        resp = await client.get(url, headers=headers)
        assert resp.status_code == 404
        resp = await client.post(url, json={"content": "sneak"}, headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_invalid_uuid_404(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = await _client_auth_header(ctx["client_user"])
        resp = await client.get("/api/v1/client/projects/not-a-uuid/comments", headers=headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════════════════════


class TestNotifications:
    @pytest.mark.asyncio
    async def test_shared_comment_sends_email(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO, logger="app.services.email")
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "shared note"},
            headers=headers,
        )
        assert resp.status_code == 201

        email_records = [r.getMessage() for r in caplog.records if "Email to=" in r.getMessage()]
        assert email_records, "no email was dispatched for shared comment"
        assert ctx["project"].name in email_records[0]

    @pytest.mark.asyncio
    async def test_internal_comment_no_email(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO, logger="app.services.email")
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])
        resp = await client.post(
            f"/api/v1/tenant/projects/{ctx['project'].id}/comments",
            json={"content": "internal", "is_internal": True},
            headers=headers,
        )
        assert resp.status_code == 201
        assert not any("Email to=" in r.getMessage() for r in caplog.records)
