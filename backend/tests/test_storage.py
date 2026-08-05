"""Storage backend + root-folder provisioning tests (FEAT-012, TODO-123/124/137)."""

from __future__ import annotations

import time
import uuid

import boto3
import pytest
from moto import mock_aws
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.enums import ClientStatus, ClientType, FileScope, TenantStatus
from app.models.file_folder import FileFolder
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant
from app.services import files as files_service
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend

# ═══════════════════════════════════════════════════════════════════════════
# LocalStorageBackend
# ═══════════════════════════════════════════════════════════════════════════


class TestLocalStorageBackend:
    @pytest.mark.anyio
    async def test_put_get_roundtrip(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        await backend.put("dir/file.txt", b"hello", "text/plain")
        assert await backend.get("dir/file.txt") == b"hello"

    @pytest.mark.anyio
    async def test_get_missing_returns_none(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert await backend.get("missing.txt") is None

    @pytest.mark.anyio
    async def test_exists(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        await backend.put("a.txt", b"x", "text/plain")
        assert await backend.exists("a.txt") is True
        assert await backend.exists("b.txt") is False

    @pytest.mark.anyio
    async def test_delete(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        await backend.put("a.txt", b"x", "text/plain")
        await backend.delete("a.txt")
        assert await backend.exists("a.txt") is False
        # deleting a missing key is a no-op
        await backend.delete("a.txt")

    @pytest.mark.anyio
    async def test_url_public_key(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert backend.url("public/img/logo.png") == "/uploads/img/logo.png"

    @pytest.mark.anyio
    async def test_url_private_key_returns_none(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        assert backend.url("tenant-1/user/x.txt") is None

    @pytest.mark.anyio
    async def test_traversal_keys_rejected(self, tmp_path):
        backend = LocalStorageBackend(tmp_path)
        for bad in ("../x", "/abs/path", "a/../b", "..", ""):
            with pytest.raises(ValueError):
                await backend.put(bad, b"x", "text/plain")
            with pytest.raises(ValueError):
                await backend.get(bad)
            with pytest.raises(ValueError):
                backend.url(bad)


# ═══════════════════════════════════════════════════════════════════════════
# S3StorageBackend (moto)
# ═══════════════════════════════════════════════════════════════════════════


class TestS3StorageBackend:
    @pytest.fixture
    def backend(self):
        with mock_aws():
            client = boto3.client(
                "s3",
                region_name="us-east-1",
                aws_access_key_id="testing",
                aws_secret_access_key="testing",
            )
            client.create_bucket(Bucket="test-bucket")
            yield S3StorageBackend(
                bucket="test-bucket",
                access_key_id="testing",
                secret_access_key="testing",
                region="us-east-1",
            )

    @pytest.mark.anyio
    async def test_put_get_roundtrip(self, backend):
        await backend.put("dir/file.txt", b"hello", "text/plain")
        assert await backend.get("dir/file.txt") == b"hello"

    @pytest.mark.anyio
    async def test_get_missing_returns_none(self, backend):
        assert await backend.get("missing.txt") is None

    @pytest.mark.anyio
    async def test_exists(self, backend):
        await backend.put("a.txt", b"x", "text/plain")
        assert await backend.exists("a.txt") is True
        assert await backend.exists("b.txt") is False

    @pytest.mark.anyio
    async def test_delete(self, backend):
        await backend.put("a.txt", b"x", "text/plain")
        await backend.delete("a.txt")
        assert await backend.exists("a.txt") is False

    @pytest.mark.anyio
    async def test_url_presigned(self, backend):
        await backend.put("dir/file.txt", b"hello", "text/plain")
        url = backend.url("dir/file.txt")
        # moto emits SigV2 presigned URLs (Signature/Expires query params)
        assert url is not None
        assert "Signature" in url
        assert "Expires" in url

    @pytest.mark.anyio
    async def test_url_expires_seconds(self, backend):
        now = time.time()
        url = backend.url("dir/file.txt", expires_seconds=600)
        expires = int(url.split("Expires=")[1].split("&")[0])
        assert now + 590 < expires <= now + 600

    @pytest.mark.anyio
    async def test_url_download_disposition(self, backend):
        url = backend.url("dir/file.txt", download=True)
        assert "response-content-disposition" in url

    @pytest.mark.anyio
    async def test_traversal_keys_rejected(self, backend):
        for bad in ("../x", "/abs/path", "a/../b"):
            with pytest.raises(ValueError):
                await backend.put(bad, b"x", "text/plain")
            with pytest.raises(ValueError):
                await backend.get(bad)


# ═══════════════════════════════════════════════════════════════════════════
# Root folder provisioning (services/files.py)
# ═══════════════════════════════════════════════════════════════════════════


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"StoragePlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=20,
        max_active_projects=50,
        max_storage_mb=1024,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant(session: AsyncSession, plan_id: uuid.UUID) -> Tenant:
    tenant = Tenant(
        business_name="StorageCo",
        slug=f"storage-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_client(session: AsyncSession, tenant_id: uuid.UUID) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name=f"Storage Client {uuid.uuid4().hex[:6]}",
        client_type=ClientType.COMPANY,
        status=ClientStatus.ACTIVE,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def _create_project(
    session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID, name: str = "Alpha"
) -> Project:
    project = Project(tenant_id=tenant_id, client_id=client_id, name=name)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


class TestEnsureRootFolders:
    @pytest.mark.anyio
    async def test_creates_three_roots_with_correct_scopes(self, db_session):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)

        folders = await files_service.ensure_root_folders(
            db_session, tenant_id=tenant.id, actor_id=uuid.uuid4()
        )

        assert set(folders) == {"My files", "Team files", "Project files"}

        q = select(FileFolder).where(FileFolder.tenant_id == tenant.id)
        rows = list((await db_session.execute(q)).scalars().all())
        scopes = {f.name: f.scope for f in rows}
        assert scopes["My files"] == FileScope.USER
        assert scopes["Team files"] == FileScope.TENANT
        assert scopes["Project files"] == FileScope.PROJECT
        assert all(f.parent_id is None for f in rows)
        assert all(f.project_id is None for f in rows)

    @pytest.mark.anyio
    async def test_idempotent(self, db_session):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)

        first = await files_service.ensure_root_folders(
            db_session, tenant_id=tenant.id, actor_id=uuid.uuid4()
        )
        second = await files_service.ensure_root_folders(
            db_session, tenant_id=tenant.id, actor_id=uuid.uuid4()
        )

        assert first == second


class TestGetProjectFolder:
    @pytest.mark.anyio
    async def test_creates_root_and_project_subfolder(self, db_session):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        client = await _create_client(db_session, tenant.id)
        project = await _create_project(db_session, tenant.id, client.id, name="Alpha")

        sub = await files_service.get_project_folder(
            db_session, tenant_id=tenant.id, project_id=project.id, actor_id=uuid.uuid4()
        )

        assert sub is not None
        assert sub.name == "Alpha"
        assert sub.scope == FileScope.PROJECT
        assert sub.project_id == project.id

        root = await db_session.get(FileFolder, sub.parent_id)
        assert root is not None
        assert root.name == "Project files"
        assert root.scope == FileScope.PROJECT
        assert root.parent_id is None

    @pytest.mark.anyio
    async def test_reuses_on_second_call(self, db_session):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        client = await _create_client(db_session, tenant.id)
        project = await _create_project(db_session, tenant.id, client.id)

        first = await files_service.get_project_folder(
            db_session, tenant_id=tenant.id, project_id=project.id, actor_id=uuid.uuid4()
        )
        second = await files_service.get_project_folder(
            db_session, tenant_id=tenant.id, project_id=project.id, actor_id=uuid.uuid4()
        )

        assert first is not None
        assert second is not None
        assert first.id == second.id

    @pytest.mark.anyio
    async def test_missing_project_returns_none(self, db_session):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)

        sub = await files_service.get_project_folder(
            db_session,
            tenant_id=tenant.id,
            project_id=uuid.uuid4(),
            actor_id=uuid.uuid4(),
        )
        assert sub is None
