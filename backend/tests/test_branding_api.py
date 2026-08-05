"""Integration tests for tenant branding (TODO-011 + FEAT-012 TODO-133):
logo upload (storage backend), public logo endpoint, PDF branding, and the
storage migration/backfill tool (TODO-126)."""

from __future__ import annotations

import base64
import re
import types
import uuid
import zlib

import boto3
import pytest
from httpx import AsyncClient
from moto import mock_aws
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
from app.storage import get_storage
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend
from scripts import migrate_storage as migrate

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
        expected_url = f"/api/v1/public/tenant/{ctx['tenant'].id}/logo"
        assert data["logo_url"] == expected_url

        profile = (await client.get("/api/v1/tenant/profile", headers=headers)).json()
        assert profile["logo_url"] == expected_url
        assert profile["branding"]["logo_url"] == expected_url
        assert profile["branding"]["logo_key"].startswith(f"public/{ctx['tenant'].id}/")

    @pytest.mark.asyncio
    async def test_public_logo_endpoint_unauthenticated(
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
        url = resp.json()["logo_url"]

        # no auth header; local backend 307-redirects to the static mount
        resp = await client.get(url, follow_redirects=True)
        assert resp.status_code == 200
        assert resp.content == _ONE_PX_PNG

        # missing tenant -> 404
        resp = await client.get(f"/api/v1/public/tenant/{uuid.uuid4()}/logo")
        assert resp.status_code == 404

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

        # logo upload (stores via the storage backend)
        resp = await client.post(
            "/api/v1/tenant/branding/logo",
            files={"file": ("logo.png", _ONE_PX_PNG, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["logo_url"] == f"/api/v1/public/tenant/{ctx['tenant'].id}/logo"

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


# ═══════════════════════════════════════════════════════════════════════════
# PDF branding via storage logo (FEAT-012, TODO-133)
# ═══════════════════════════════════════════════════════════════════════════


class TestInvoicePdfStorageLogo:
    @pytest.mark.asyncio
    async def test_pdf_renders_with_storage_logo_and_color(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])

        # seed logo bytes directly into storage + branding (as upload would)
        tenant = ctx["tenant"]
        key = f"public/{tenant.id}/logo.png"
        await get_storage().put(key, _ONE_PX_PNG, "image/png")
        tenant.branding = {
            "color": "#336699",
            "logo_key": key,
            "logo_url": f"/api/v1/public/tenant/{tenant.id}/logo",
        }
        tenant.logo_url = tenant.branding["logo_url"]
        await db_session.flush()

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
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:4] == b"%PDF"


# ═══════════════════════════════════════════════════════════════════════════
# PDF currency code (FEAT-014, TODO-151)
# ═══════════════════════════════════════════════════════════════════════════


def _decompress_pdf_streams(pdf_bytes: bytes) -> bytes:
    """Extract every stream object and decode ASCII85 + Flate content.

    ReportLab writes content streams with [/ASCII85Decode /FlateDecode].
    Returns the concatenated decoded bytes; undecodable streams are skipped.
    """
    decoded = bytearray()
    for match in re.finditer(rb"stream\r?\n", pdf_bytes):
        start = match.end()
        end = pdf_bytes.find(b"endstream", start)
        if end == -1:
            continue
        raw = pdf_bytes[start:end]
        raw = raw.rstrip(b"\r\n")
        if not raw:
            continue
        try:
            inflated = zlib.decompress(base64.a85decode(raw, adobe=True))
            decoded.extend(inflated)
        except (ValueError, zlib.error):
            # non-content streams (fonts, images) use other encodings; skip
            continue
    return bytes(decoded)


class TestInvoicePdfCurrencyCode:
    @pytest.mark.asyncio
    async def test_pdf_uses_tenant_currency_code(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])

        resp = await client.patch(
            "/api/v1/tenant/settings/currency",
            json={"value": "BDT"},
            headers=headers,
        )
        assert resp.status_code == 200

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
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

        content = _decompress_pdf_streams(resp.content)
        assert b"BDT" in content
        # service default price is 500.00 -> code-prefixed money string
        assert b"BDT 500.00" in content

    @pytest.mark.asyncio
    async def test_pdf_defaults_to_usd_code(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        ctx = await _bootstrap(db_session)
        headers = await _admin_auth_header(ctx["admin"])

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
        await client.post(f"/api/v1/tenant/invoices/{inv_id}/issue", headers=headers)

        resp = await client.get(f"/api/v1/tenant/invoices/{inv_id}/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

        content = _decompress_pdf_streams(resp.content)
        assert b"USD" in content
        assert b"USD 500.00" in content


# ═══════════════════════════════════════════════════════════════════════════
# Storage migration/backfill tool (FEAT-012, TODO-126)
# ═══════════════════════════════════════════════════════════════════════════


class TestBackfillLegacyLogos:
    @pytest.mark.asyncio
    async def test_backfill_migrates_legacy_uploads_logo(
        self, db_session: AsyncSession, tmp_path, monkeypatch
    ):
        ctx = await _bootstrap(db_session)
        tenant = ctx["tenant"]
        tenant.branding = {"logo_url": "/uploads/legacy.png"}
        await db_session.flush()

        uploads_dir = tmp_path / "uploads"
        uploads_dir.mkdir()
        (uploads_dir / "legacy.png").write_bytes(b"legacy-logo-bytes")

        store = LocalStorageBackend(tmp_path / "store")
        monkeypatch.setattr(
            migrate,
            "get_settings",
            lambda: types.SimpleNamespace(uploads_dir=str(uploads_dir)),
        )
        monkeypatch.setattr(migrate, "get_storage", lambda: store)

        count = await migrate.backfill_legacy_logos(db_session)
        assert count == 1

        key = f"public/{tenant.id}/legacy.png"
        assert tenant.branding["logo_key"] == key
        assert tenant.branding["logo_url"] == f"/api/v1/public/tenant/{tenant.id}/logo"
        assert tenant.logo_url == tenant.branding["logo_url"]
        assert await store.get(key) == b"legacy-logo-bytes"

    @pytest.mark.asyncio
    async def test_backfill_idempotent_and_skips_missing(
        self, db_session: AsyncSession, tmp_path, monkeypatch
    ):
        ctx = await _bootstrap(db_session)
        tenant = ctx["tenant"]
        tenant.branding = {"logo_url": "/uploads/ghost.png"}  # file missing on disk
        await db_session.flush()

        uploads_dir = tmp_path / "uploads"
        uploads_dir.mkdir()
        store = LocalStorageBackend(tmp_path / "store")
        monkeypatch.setattr(
            migrate,
            "get_settings",
            lambda: types.SimpleNamespace(uploads_dir=str(uploads_dir)),
        )
        monkeypatch.setattr(migrate, "get_storage", lambda: store)

        assert await migrate.backfill_legacy_logos(db_session) == 0
        # unchanged: still legacy URL, no key written
        assert tenant.branding["logo_url"] == "/uploads/ghost.png"
        assert "logo_key" not in tenant.branding


class TestTransferKeys:
    @pytest.mark.asyncio
    async def test_transfer_local_to_s3(self, tmp_path):
        local = LocalStorageBackend(tmp_path / "local")
        await local.put("public/a.txt", b"aaa", "text/plain")
        await local.put("public/b.txt", b"bbb", "text/plain")

        with mock_aws():
            boto3_client = boto3.client(
                "s3",
                region_name="us-east-1",
                aws_access_key_id="testing",
                aws_secret_access_key="testing",
            )
            boto3_client.create_bucket(Bucket="test-bucket")
            s3 = S3StorageBackend(
                bucket="test-bucket",
                access_key_id="testing",
                secret_access_key="testing",
                region="us-east-1",
            )

            transferred, total_bytes = await migrate.transfer_keys(
                local,
                s3,
                keys=["public/a.txt", "public/b.txt"],
            )
            assert transferred == 2
            assert total_bytes == 6
            assert await s3.get("public/a.txt") == b"aaa"
            assert await s3.get("public/b.txt") == b"bbb"

    @pytest.mark.asyncio
    async def test_transfer_skips_missing_source_keys(self, tmp_path):
        local = LocalStorageBackend(tmp_path / "local")
        await local.put("a.txt", b"x", "text/plain")

        with mock_aws():
            boto3_client = boto3.client(
                "s3",
                region_name="us-east-1",
                aws_access_key_id="testing",
                aws_secret_access_key="testing",
            )
            boto3_client.create_bucket(Bucket="test-bucket")
            s3 = S3StorageBackend(
                bucket="test-bucket",
                access_key_id="testing",
                secret_access_key="testing",
                region="us-east-1",
            )

            transferred, total_bytes = await migrate.transfer_keys(
                local, s3, keys=["a.txt", "missing.txt"]
            )
            assert transferred == 1
            assert total_bytes == 1
            assert await s3.get("a.txt") == b"x"
