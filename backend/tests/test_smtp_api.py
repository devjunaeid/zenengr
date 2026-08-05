"""Integration tests for per-tenant SMTP config API (FEAT-013).

Covers: masked GET, upsert + password masking/encryption, password
preservation on partial update, validation, test-email endpoint
(not-configured / failure / success), encryption roundtrip, sender
factory fallback, and RBAC for writes.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.enums import (
    AdminUserRole,
    BillingCycle,
    SmtpSecurityMode,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.models.tenant_smtp_config import TenantSmtpConfig
from app.models.tenant_subscription import TenantSubscription
from app.services import smtp as smtp_service
from app.services import tenant_smtp as tenant_smtp_service

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession) -> Plan:
    plan = Plan(
        name=f"TestPlan-{uuid.uuid4().hex[:8]}",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _create_tenant_and_admin(
    session: AsyncSession,
) -> tuple[Tenant, AdminUser]:
    plan = await _create_plan(session)
    tenant = Tenant(
        business_name="SmtpCo",
        slug=f"smtp-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan.id,
    )
    session.add(tenant)
    await session.flush()
    session.add(
        TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
        )
    )
    admin = AdminUser(
        tenant_id=tenant.id,
        email=f"admin-{uuid.uuid4().hex[:8]}@smtpco.com",
        full_name="SMTP Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(tenant)
    await session.refresh(admin)
    return tenant, admin


async def _create_user(
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


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


async def _get_row(db_session: AsyncSession, tenant_id: uuid.UUID) -> TenantSmtpConfig | None:
    stmt = select(TenantSmtpConfig).where(TenantSmtpConfig.tenant_id == tenant_id)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


# ═══════════════════════════════════════════════════════════════════════════
# CRUD (TODO-139)
# ═══════════════════════════════════════════════════════════════════════════


class TestSmtpConfigCrud:
    """GET/PATCH /api/v1/tenant/smtp-config"""

    @pytest.mark.anyio
    async def test_get_empty_config(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.get("/api/v1/tenant/smtp-config/", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["host"] is None
        assert data["port"] is None
        assert data["username"] is None
        assert data["from_email"] is None
        assert data["from_name"] is None
        assert data["mode"] == "starttls"
        assert data["enabled"] is False
        assert data["has_password"] is False
        assert "password" not in data
        assert "password_ciphertext" not in data

    @pytest.mark.anyio
    async def test_upsert_and_masking(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        payload = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "app@example.com",
            "password": "hunter2-secret",
            "from_email": "noreply@example.com",
            "from_name": "ZenEngr",
            "mode": "ssl",
            "enabled": True,
        }
        resp = await client.patch("/api/v1/tenant/smtp-config/", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["host"] == "smtp.example.com"
        assert data["port"] == 587
        assert data["username"] == "app@example.com"
        assert data["from_email"] == "noreply@example.com"
        assert data["from_name"] == "ZenEngr"
        assert data["mode"] == "ssl"
        assert data["enabled"] is True
        assert data["has_password"] is True
        assert "hunter2-secret" not in str(data)
        assert "password" not in data
        assert "password_ciphertext" not in data

        # GET returns the same masked shape
        resp = await client.get("/api/v1/tenant/smtp-config/", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["has_password"] is True

        # Row in DB holds Fernet ciphertext; decrypt matches the original
        row = await _get_row(db_session, tenant.id)
        assert row is not None
        assert row.password_ciphertext is not None
        assert "hunter2-secret" not in row.password_ciphertext
        assert smtp_service.decrypt_password(row.password_ciphertext) == "hunter2-secret"

    @pytest.mark.anyio
    async def test_update_without_password_keeps(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        await client.patch(
            "/api/v1/tenant/smtp-config/",
            json={
                "host": "smtp.example.com",
                "port": 587,
                "username": "app@example.com",
                "password": "orig-secret",
                "from_email": "noreply@example.com",
                "mode": "starttls",
                "enabled": True,
            },
            headers=headers,
        )

        resp = await client.patch(
            "/api/v1/tenant/smtp-config/",
            json={"host": "smtp-new.example.com"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["host"] == "smtp-new.example.com"
        assert data["has_password"] is True

        row = await _get_row(db_session, tenant.id)
        assert row is not None
        assert row.password_ciphertext is not None
        assert smtp_service.decrypt_password(row.password_ciphertext) == "orig-secret"

    @pytest.mark.anyio
    async def test_validation(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        # enabled without host/from_email -> 422
        resp = await client.patch(
            "/api/v1/tenant/smtp-config/", json={"enabled": True}, headers=headers
        )
        assert resp.status_code == 422

        # port 0 -> 422
        resp = await client.patch("/api/v1/tenant/smtp-config/", json={"port": 0}, headers=headers)
        assert resp.status_code == 422

        # mode "bogus" -> 422
        resp = await client.patch(
            "/api/v1/tenant/smtp-config/", json={"mode": "bogus"}, headers=headers
        )
        assert resp.status_code == 422

        # bad from_email -> 422
        resp = await client.patch(
            "/api/v1/tenant/smtp-config/",
            json={"from_email": "not-an-email"},
            headers=headers,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Test-email endpoint (TODO-141)
# ═══════════════════════════════════════════════════════════════════════════


class TestSmtpTestEndpoint:
    """POST /api/v1/tenant/smtp-config/test"""

    @pytest.mark.anyio
    async def test_test_endpoint_not_configured(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.post("/api/v1/tenant/smtp-config/test", headers=headers)
        assert resp.status_code == 422
        assert "SMTP not configured" in str(resp.json())

    @pytest.mark.anyio
    async def test_test_endpoint_failure_surfaces(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)
        await client.patch(
            "/api/v1/tenant/smtp-config/",
            json={
                "host": "127.0.0.1",
                "port": 1,
                "from_email": "noreply@example.com",
                "enabled": True,
            },
            headers=headers,
        )

        resp = await client.post("/api/v1/tenant/smtp-config/test", headers=headers)
        assert resp.status_code == 422
        assert "Failed to send test email" in str(resp.json())

    @pytest.mark.anyio
    async def test_test_endpoint_success(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)
        await client.patch(
            "/api/v1/tenant/smtp-config/",
            json={
                "host": "smtp.example.com",
                "port": 587,
                "username": "app@example.com",
                "password": "pw",
                "from_email": "noreply@example.com",
                "from_name": "ZenEngr",
                "mode": "ssl",
                "enabled": True,
            },
            headers=headers,
        )

        sent: dict[str, Any] = {}

        async def _fake_send_email(self: Any, to: str, subject: str, body: str, **_: Any) -> None:
            sent["to"] = to
            sent["subject"] = subject
            sent["body"] = body

        monkeypatch.setattr(smtp_service.SmtpEmailSender, "send_email", _fake_send_email)

        resp = await client.post(
            "/api/v1/tenant/smtp-config/test",
            json={"to_email": "boss@example.com"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["message"] == "Test email sent"
        assert sent["to"] == "boss@example.com"
        assert sent["subject"] == "ZenEngr SMTP test"
        assert sent["body"]


# ═══════════════════════════════════════════════════════════════════════════
# Encryption + sender factory
# ═══════════════════════════════════════════════════════════════════════════


class TestSmtpInternals:
    """encrypt/decrypt helpers + get_sender_for_tenant factory."""

    @pytest.mark.anyio
    async def test_encryption_roundtrip(self):
        plain = "p@ssw0rd-123"
        ct = smtp_service.encrypt_password(plain)
        assert ct != plain
        assert smtp_service.decrypt_password(ct) == plain

    @pytest.mark.anyio
    async def test_sender_factory(self, db_session: AsyncSession):
        from app.services.email import ConsoleEmailSender

        tenant, _ = await _create_tenant_and_admin(db_session)

        # No config -> console fallback
        sender = await smtp_service.get_sender_for_tenant(db_session, tenant_id=tenant.id)
        assert isinstance(sender, ConsoleEmailSender)

        # Disabled config -> console fallback
        await tenant_smtp_service.upsert_smtp_config(
            db_session,
            tenant_id=tenant.id,
            data={
                "host": "smtp.example.com",
                "port": 587,
                "from_email": "noreply@example.com",
                "mode": SmtpSecurityMode.SSL,
                "enabled": False,
            },
            actor_id=None,
        )
        sender = await smtp_service.get_sender_for_tenant(db_session, tenant_id=tenant.id)
        assert isinstance(sender, ConsoleEmailSender)

        # Enabled + configured -> SmtpEmailSender with right host/mode/password
        await tenant_smtp_service.upsert_smtp_config(
            db_session,
            tenant_id=tenant.id,
            data={
                "host": "smtp.example.com",
                "port": 465,
                "username": "app@example.com",
                "password": "hunter2",
                "from_email": "noreply@example.com",
                "from_name": "ZenEngr",
                "mode": SmtpSecurityMode.SSL,
                "enabled": True,
            },
            actor_id=None,
        )
        sender = await smtp_service.get_sender_for_tenant(db_session, tenant_id=tenant.id)
        assert isinstance(sender, smtp_service.SmtpEmailSender)
        assert sender.host == "smtp.example.com"
        assert sender.port == 465
        assert sender.username == "app@example.com"
        assert sender.mode == SmtpSecurityMode.SSL
        assert sender.password == "hunter2"  # decrypted from ciphertext
        assert sender.from_email == "noreply@example.com"
        assert sender.from_name == "ZenEngr"


# ═══════════════════════════════════════════════════════════════════════════
# RBAC (FR-4.2)
# ═══════════════════════════════════════════════════════════════════════════


class TestSmtpRbac:
    @pytest.mark.anyio
    async def test_employee_forbidden(self, client: AsyncClient, db_session: AsyncSession):
        tenant, _ = await _create_tenant_and_admin(db_session)
        employee = await _create_user(
            db_session,
            f"emp-{uuid.uuid4().hex[:8]}@smtpco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(employee)

        resp = await client.patch(
            "/api/v1/tenant/smtp-config/", json={"host": "x"}, headers=headers
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_employee_can_read(self, client: AsyncClient, db_session: AsyncSession):
        tenant, _ = await _create_tenant_and_admin(db_session)
        employee = await _create_user(
            db_session,
            f"emp-read-{uuid.uuid4().hex[:8]}@smtpco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(employee)

        resp = await client.get("/api/v1/tenant/smtp-config/", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["has_password"] is False
