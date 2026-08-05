"""Integration tests for client portal file access (FEAT-012, TODO-132)."""

from __future__ import annotations

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
        name=f"FilesPlan-{uuid.uuid4().hex[:8]}",
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
        business_name="FilesCo",
        slug=f"filesco-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_admin(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=f"admin-{uuid.uuid4().hex[:8]}@filesco.com",
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
        name=f"Files Client {uuid.uuid4().hex[:6]}",
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


def _admin_auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


def _client_auth_header(user: ClientUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role="client_user",
        realm="client",
        client_id=str(user.client_id),
    )
    return {"Authorization": f"Bearer {token}"}


async def _upload(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    scope: str,
    filename: str = "a.txt",
    content: bytes = b"hello",
    project_id: uuid.UUID | None = None,
):
    data: dict[str, str] = {"scope": scope}
    if project_id is not None:
        data["project_id"] = str(project_id)
    return await client.post(
        "/api/v1/tenant/files/upload",
        files={"file": (filename, content, "text/plain")},
        data=data,
        headers=headers,
    )


async def _bootstrap(db_session: AsyncSession):
    """Plan + tenant + admin + clients A/B with client users."""
    plan = await _create_plan(db_session)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(db_session, tenant.id)
    client_a = await _create_client(db_session, tenant.id)
    client_b = await _create_client(db_session, tenant.id)
    cu_a = await _create_client_user(db_session, client_a.id, tenant.id)
    cu_b = await _create_client_user(db_session, client_b.id, tenant.id)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "client_a": client_a,
        "client_b": client_b,
        "cu_a": cu_a,
        "cu_b": cu_b,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Client project file list + download (TODO-132)
# ═══════════════════════════════════════════════════════════════════════════


class TestClientProjectFiles:
    @pytest.mark.asyncio
    async def test_client_lists_own_project_files(self, client, db_session):
        ctx = await _bootstrap(db_session)
        admin_headers = _admin_auth_header(ctx["admin"])
        proj_a = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        proj_b = await _create_project(db_session, ctx["tenant"].id, ctx["client_b"].id)

        resp = await _upload(
            client,
            admin_headers,
            scope="project",
            project_id=proj_a.id,
            filename="doc.pdf",
            content=b"%PDF-fake",
        )
        assert resp.status_code == 201
        file_id = resp.json()["id"]

        # another project file for client B's project must not leak into A
        await _upload(
            client,
            admin_headers,
            scope="project",
            project_id=proj_b.id,
            filename="other.txt",
            content=b"other",
        )

        resp = await client.get(
            f"/api/v1/client/projects/{proj_a.id}/files",
            headers=_client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 20
        item = data["items"][0]
        assert item["id"] == file_id
        assert item["name"] == "doc.pdf"
        assert item["scope"] == "project"
        assert item["project_id"] == str(proj_a.id)
        assert item["size_bytes"] == 9

    @pytest.mark.asyncio
    async def test_other_client_project_files_404(self, client, db_session):
        ctx = await _bootstrap(db_session)
        admin_headers = _admin_auth_header(ctx["admin"])
        proj_a = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)
        await _upload(client, admin_headers, scope="project", project_id=proj_a.id)

        resp = await client.get(
            f"/api/v1/client/projects/{proj_a.id}/files",
            headers=_client_auth_header(ctx["cu_b"]),
        )
        assert resp.status_code == 404

        # malformed id -> 404
        resp = await client.get(
            "/api/v1/client/projects/not-a-uuid/files",
            headers=_client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_downloads_own_project_file(self, client, db_session):
        ctx = await _bootstrap(db_session)
        admin_headers = _admin_auth_header(ctx["admin"])
        proj_a = await _create_project(db_session, ctx["tenant"].id, ctx["client_a"].id)

        resp = await _upload(
            client,
            admin_headers,
            scope="project",
            project_id=proj_a.id,
            filename="doc.txt",
            content=b"secret-doc",
        )
        file_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/client/files/{file_id}/content",
            headers=_client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 200
        assert resp.content == b"secret-doc"
        assert resp.headers["content-disposition"].startswith("attachment;")

        # audited as CLIENT_USER
        rows = (
            (
                await db_session.execute(
                    select(AuditLog).where(
                        AuditLog.tenant_id == ctx["tenant"].id,
                        AuditLog.action == "file.downloaded",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].actor_type.value == "client_user"
        assert rows[0].actor_id == ctx["cu_a"].id
        assert rows[0].entity_id == file_id
        assert rows[0].details["name"] == "doc.txt"

    @pytest.mark.asyncio
    async def test_client_tenant_scope_file_404(self, client, db_session):
        ctx = await _bootstrap(db_session)
        admin_headers = _admin_auth_header(ctx["admin"])
        resp = await _upload(client, admin_headers, scope="tenant", filename="team.txt")
        tenant_file_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/client/files/{tenant_file_id}/content",
            headers=_client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404

        # other client's project file -> 404
        proj_b = await _create_project(db_session, ctx["tenant"].id, ctx["client_b"].id)
        resp = await _upload(
            client,
            admin_headers,
            scope="project",
            project_id=proj_b.id,
            filename="b.txt",
        )
        proj_b_file_id = resp.json()["id"]
        resp = await client.get(
            f"/api/v1/client/files/{proj_b_file_id}/content",
            headers=_client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404

        # malformed id -> 404
        resp = await client.get(
            "/api/v1/client/files/not-a-uuid/content",
            headers=_client_auth_header(ctx["cu_a"]),
        )
        assert resp.status_code == 404
