"""Integration tests for tenant file APIs (FEAT-012, TODO-127/128/129/130/131/136)."""

from __future__ import annotations

import types
import uuid

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
from app.models.tenant import Tenant
from app.services import files as files_service

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession, *, max_storage_mb: int = 256) -> Plan:
    plan = Plan(
        name=f"FilesPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=20,
        max_active_projects=50,
        max_storage_mb=max_storage_mb,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant(
    session: AsyncSession,
    plan_id: uuid.UUID,
) -> Tenant:
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
        name=f"Files Client {uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Project:
    project = Project(
        tenant_id=tenant_id,
        name=f"Files Proj {uuid.uuid4().hex[:6]}",
        client_id=client_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


def _auth_header(user: AdminUser) -> dict[str, str]:
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
    max_storage_mb: int = 256,
):
    """Create plan + tenant + admin + employee + client + project."""
    plan = await _create_plan(db_session, max_storage_mb=max_storage_mb)
    tenant = await _create_tenant(db_session, plan.id)
    admin = await _create_admin(
        db_session,
        f"admin-{uuid.uuid4().hex[:8]}@filesco.com",
        AdminUserRole.ADMIN,
        tenant.id,
    )
    employee = await _create_admin(
        db_session,
        f"emp-{uuid.uuid4().hex[:8]}@filesco.com",
        AdminUserRole.EMPLOYEE,
        tenant.id,
    )
    client = await _create_client(db_session, tenant.id)
    project = await _create_project(db_session, tenant.id, client.id)
    return {
        "plan": plan,
        "tenant": tenant,
        "admin": admin,
        "employee": employee,
        "client": client,
        "project": project,
    }


async def _upload(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    scope: str,
    filename: str = "a.txt",
    content: bytes = b"hello",
    folder_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
):
    data: dict[str, str] = {"scope": scope}
    if folder_id is not None:
        data["folder_id"] = str(folder_id)
    if project_id is not None:
        data["project_id"] = str(project_id)
    return await client.post(
        "/api/v1/tenant/files/upload",
        files={"file": (filename, content, "text/plain")},
        data=data,
        headers=headers,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Upload + listing
# ═══════════════════════════════════════════════════════════════════════════


class TestUploadAndList:
    @pytest.mark.asyncio
    async def test_upload_user_file_and_list_own(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        other = await _create_admin(
            db_session,
            f"other-{uuid.uuid4().hex[:8]}@filesco.com",
            AdminUserRole.ADMIN,
            ctx["tenant"].id,
        )
        headers = _auth_header(ctx["admin"])
        resp = await _upload(client, headers, scope="user")
        assert resp.status_code == 201
        data = resp.json()
        assert data["scope"] == "user"
        assert data["name"] == "a.txt"
        assert data["size_bytes"] == 5
        assert data["folder_id"] is None

        resp = await client.get("/api/v1/tenant/files/?scope=user", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["id"] == data["id"]

        resp = await client.get("/api/v1/tenant/files/?scope=user", headers=_auth_header(other))
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_upload_tenant_file_visible_to_all_staff(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await _upload(client, _auth_header(ctx["admin"]), scope="tenant")
        assert resp.status_code == 201

        resp = await client.get(
            "/api/v1/tenant/files/?scope=tenant",
            headers=_auth_header(ctx["employee"]),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_employee_upload_tenant(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await _upload(client, _auth_header(ctx["employee"]), scope="tenant")
        assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════
# Download
# ═══════════════════════════════════════════════════════════════════════════


class TestDownload:
    @pytest.mark.asyncio
    async def test_download_own_and_deny_other_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        other = await _create_admin(
            db_session,
            f"other-{uuid.uuid4().hex[:8]}@filesco.com",
            AdminUserRole.ADMIN,
            ctx["tenant"].id,
        )
        headers = _auth_header(ctx["admin"])
        resp = await _upload(client, headers, scope="user")
        file_id = resp.json()["id"]

        resp = await client.get(f"/api/v1/tenant/files/{file_id}/content", headers=headers)
        assert resp.status_code == 200
        assert resp.content == b"hello"

        resp = await client.get(
            f"/api/v1/tenant/files/{file_id}/content",
            headers=_auth_header(other),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_tenant_file_any_staff(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        resp = await _upload(client, _auth_header(ctx["admin"]), scope="tenant")
        file_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/tenant/files/{file_id}/content",
            headers=_auth_header(ctx["employee"]),
        )
        assert resp.status_code == 200
        assert resp.content == b"hello"

    @pytest.mark.asyncio
    async def test_upload_project_file_requires_project(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = _auth_header(ctx["admin"])

        resp = await _upload(client, headers, scope="project")
        assert resp.status_code == 422

        resp = await _upload(client, headers, scope="project", project_id=uuid.uuid4())
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_project_file_staff_download(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        resp = await _upload(
            client,
            _auth_header(ctx["admin"]),
            scope="project",
            project_id=ctx["project"].id,
        )
        assert resp.status_code == 201
        file_id = resp.json()["id"]

        resp = await client.get(
            f"/api/v1/tenant/files/{file_id}/content",
            headers=_auth_header(ctx["employee"]),
        )
        assert resp.status_code == 200
        assert resp.content == b"hello"

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
        assert rows[0].entity_type == "file"
        assert rows[0].entity_id == file_id
        assert rows[0].details["file_id"] == file_id
        assert rows[0].details["name"] == "a.txt"


# ═══════════════════════════════════════════════════════════════════════════
# Delete / rename / move
# ═══════════════════════════════════════════════════════════════════════════


class TestFileMutations:
    @pytest.mark.asyncio
    async def test_delete_rules(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        other = await _create_admin(
            db_session,
            f"other-{uuid.uuid4().hex[:8]}@filesco.com",
            AdminUserRole.ADMIN,
            ctx["tenant"].id,
        )
        headers = _auth_header(ctx["admin"])

        # USER file: owner deletes, other user gets 404
        user_file = (await _upload(client, headers, scope="user")).json()["id"]
        resp = await client.delete(
            f"/api/v1/tenant/files/{user_file}",
            headers=_auth_header(other),
        )
        assert resp.status_code == 404
        resp = await client.delete(f"/api/v1/tenant/files/{user_file}", headers=headers)
        assert resp.status_code == 204

        # TENANT file: employee gets 404, admin deletes
        tenant_file = (await _upload(client, headers, scope="tenant")).json()["id"]
        resp = await client.delete(
            f"/api/v1/tenant/files/{tenant_file}",
            headers=_auth_header(ctx["employee"]),
        )
        assert resp.status_code == 404
        resp = await client.delete(f"/api/v1/tenant/files/{tenant_file}", headers=headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_rename_and_move(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = _auth_header(ctx["admin"])

        # TENANT folder
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "TeamFolder", "scope": "tenant"},
            headers=headers,
        )
        assert resp.status_code == 201
        folder_id = resp.json()["id"]

        # PROJECT folder (for the wrong-scope move target)
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={
                "name": "ProjFolder",
                "scope": "project",
                "project_id": str(ctx["project"].id),
            },
            headers=headers,
        )
        assert resp.status_code == 201
        proj_folder_id = resp.json()["id"]

        file_id = (await _upload(client, headers, scope="tenant")).json()["id"]

        resp = await client.patch(
            f"/api/v1/tenant/files/{file_id}",
            json={"name": "renamed.txt"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "renamed.txt"

        resp = await client.post(
            f"/api/v1/tenant/files/{file_id}/move",
            json={"folder_id": str(folder_id)},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["folder_id"] == str(folder_id)

        resp = await client.post(
            f"/api/v1/tenant/files/{file_id}/move",
            json={"folder_id": str(proj_folder_id)},
            headers=headers,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Folders
# ═══════════════════════════════════════════════════════════════════════════


class TestFolders:
    @pytest.mark.asyncio
    async def test_folders(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session)
        headers = _auth_header(ctx["admin"])

        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "Alpha", "scope": "tenant"},
            headers=headers,
        )
        assert resp.status_code == 201
        alpha_id = resp.json()["id"]

        # duplicate name -> 409
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "Alpha", "scope": "tenant"},
            headers=headers,
        )
        assert resp.status_code == 409

        # nested folder
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "Beta", "scope": "tenant", "parent_id": alpha_id},
            headers=headers,
        )
        assert resp.status_code == 201
        beta_id = resp.json()["id"]

        # cross-scope: PROJECT child under a TENANT parent -> 422
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={
                "name": "Bad",
                "scope": "project",
                "project_id": str(ctx["project"].id),
                "parent_id": alpha_id,
            },
            headers=headers,
        )
        assert resp.status_code == 422

        # rename
        resp = await client.patch(
            f"/api/v1/tenant/files/folders/{alpha_id}",
            json={"name": "AlphaRenamed"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "AlphaRenamed"

        # tree shows real roots + nested child
        resp = await client.get("/api/v1/tenant/files/folders", headers=headers)
        assert resp.status_code == 200
        tree = resp.json()
        names = {node["name"] for node in tree}
        assert names == {
            "My files",
            "Team files",
            "Project files",
            "AlphaRenamed",
        }
        team = next(n for n in tree if n["name"] == "Team files")
        assert team["id"] is not None
        assert team["children"] == []
        alpha_node = next(n for n in tree if n["name"] == "AlphaRenamed")
        assert {c["name"] for c in alpha_node["children"]} == {"Beta"}
        my_files = next(n for n in tree if n["name"] == "My files")
        assert my_files["id"] is None
        assert my_files["scope"] == "user"

        # delete non-empty -> 409; empty -> 204
        resp = await client.delete(f"/api/v1/tenant/files/folders/{alpha_id}", headers=headers)
        assert resp.status_code == 409
        resp = await client.delete(f"/api/v1/tenant/files/folders/{beta_id}", headers=headers)
        assert resp.status_code == 204
        resp = await client.delete(f"/api/v1/tenant/files/folders/{alpha_id}", headers=headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_user_scope_folder_per_user_isolation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        other = await _create_admin(
            db_session,
            f"other-{uuid.uuid4().hex[:8]}@filesco.com",
            AdminUserRole.ADMIN,
            ctx["tenant"].id,
        )
        headers = _auth_header(ctx["admin"])
        other_headers = _auth_header(other)

        def _all_ids(nodes: list[dict]) -> set[str]:
            ids: set[str] = set()
            for node in nodes:
                if node["id"] is not None:
                    ids.add(node["id"])
                ids |= _all_ids(node["children"])
            return ids

        # own USER folder -> 201
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "MyStuff", "scope": "user"},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["scope"] == "user"
        folder_id = resp.json()["id"]

        # same user, same name -> 409
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "MyStuff", "scope": "user"},
            headers=headers,
        )
        assert resp.status_code == 409

        # second user, same name -> 201 (per-user isolation)
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "MyStuff", "scope": "user"},
            headers=other_headers,
        )
        assert resp.status_code == 201
        other_folder_id = resp.json()["id"]
        assert other_folder_id != folder_id

        # nested USER folder under own USER folder -> 201 (recursive tree)
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "Sub", "scope": "user", "parent_id": str(folder_id)},
            headers=headers,
        )
        assert resp.status_code == 201

        # USER folder under a TENANT folder -> 422 (parent scope mismatch)
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "TeamStuff", "scope": "tenant"},
            headers=headers,
        )
        assert resp.status_code == 201
        team_id = resp.json()["id"]
        resp = await client.post(
            "/api/v1/tenant/files/folders",
            json={"name": "Nested", "scope": "user", "parent_id": str(team_id)},
            headers=headers,
        )
        assert resp.status_code == 422

        # USER folder appears in own tree only (recursive), hidden from others
        resp = await client.get("/api/v1/tenant/files/folders", headers=headers)
        assert resp.status_code == 200
        my_files = next(n for n in resp.json() if n["name"] == "My files")
        assert [c["name"] for c in my_files["children"]] == ["MyStuff"]
        assert [c["name"] for c in my_files["children"][0]["children"]] == ["Sub"]
        assert folder_id in _all_ids(resp.json())
        assert other_folder_id not in _all_ids(resp.json())

        resp = await client.get("/api/v1/tenant/files/folders", headers=other_headers)
        assert resp.status_code == 200
        assert other_folder_id in _all_ids(resp.json())
        assert folder_id not in _all_ids(resp.json())

        # upload into own USER folder works; other user -> 404
        resp = await _upload(client, headers, scope="user", folder_id=folder_id)
        assert resp.status_code == 201
        resp = await client.get(
            f"/api/v1/tenant/files/?folder_id={folder_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = await _upload(client, other_headers, scope="user", folder_id=folder_id)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Quota + size cap
# ═══════════════════════════════════════════════════════════════════════════


class TestLimits:
    @pytest.mark.asyncio
    async def test_quota_exceeded(self, client: AsyncClient, db_session: AsyncSession):
        ctx = await _bootstrap(db_session, max_storage_mb=1)
        resp = await _upload(
            client,
            _auth_header(ctx["admin"]),
            scope="tenant",
            filename="big.bin",
            content=b"x" * (2 * 1024 * 1024),
        )
        assert resp.status_code == 413
        assert "quota" in resp.json()["error"]["message"]

    @pytest.mark.asyncio
    async def test_upload_size_cap(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        ctx = await _bootstrap(db_session)
        monkeypatch.setattr(
            files_service,
            "get_settings",
            lambda: types.SimpleNamespace(file_max_upload_mb=1),
        )
        resp = await _upload(
            client,
            _auth_header(ctx["admin"]),
            scope="tenant",
            filename="big.bin",
            content=b"x" * (2 * 1024 * 1024),
        )
        assert resp.status_code == 413
        assert "maximum upload size" in resp.json()["error"]["message"]
