"""Integration tests for FEAT-011 self-service account endpoints.

TODO-109 profile edit, TODO-113 change password, TODO-114 forgot password,
TODO-115 password policy, TODO-119 activity history.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.client_invite import ClientInvite
from app.models.client_user import ClientUser
from app.models.enums import (
    AdminUserRole,
    ClientStatus,
    ClientType,
    PermissionLevel,
    TenantStatus,
)
from app.models.plan import Plan
from app.models.project import Project
from app.models.tenant import Tenant
from app.models.tenant_setting import TenantSetting

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


async def _create_tenant(
    session: AsyncSession, plan_id: uuid.UUID, status: TenantStatus = TenantStatus.ACTIVE
) -> Tenant:
    tenant = Tenant(
        business_name="TestCo",
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status=status,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def _create_user(
    session: AsyncSession,
    email: str,
    role: AdminUserRole,
    tenant_id: uuid.UUID | None = None,
    is_active: bool = True,
) -> AdminUser:
    user = AdminUser(
        tenant_id=tenant_id,
        email=email,
        full_name=f"Test {role.value}",
        hashed_password=hash_password(_TEST_PWD),
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_client(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    status: ClientStatus = ClientStatus.ACTIVE,
    email: str | None = None,
) -> Client:
    client = Client(
        tenant_id=tenant_id,
        name="TestClient",
        client_type=ClientType.COMPANY,
        status=status,
        email=email,
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
    is_active: bool = True,
) -> ClientUser:
    cu = ClientUser(
        client_id=client_id,
        tenant_id=tenant_id,
        email=email,
        full_name="Test Client User",
        hashed_password=hash_password(_TEST_PWD),
        is_active=is_active,
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


def _extract_raw_token_from_log(caplog, email: str) -> str | None:
    """Extract raw reset token from console email log."""
    for record in caplog.records:
        if email in record.getMessage():
            match = re.search(r"token=([A-Za-z0-9_-]+)", record.getMessage())
            if match:
                return match.group(1)
    return None


async def _set_password_min_length(
    session: AsyncSession, tenant_id: uuid.UUID, value: str = "14"
) -> None:
    setting = TenantSetting(
        tenant_id=tenant_id,
        key="password_min_length",
        value=value,
        permission_level=PermissionLevel.TENANT_ADMIN_EDITABLE,
    )
    session.add(setting)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Profile
# ═══════════════════════════════════════════════════════════════════════════


class TestProfile:
    @pytest.mark.anyio
    async def test_admin_updates_profile(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"prof-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            "/api/v1/auth/profile",
            json={
                "full_name": "Updated Name",
                "phone": "555-1234",
                "timezone": "America/New_York",
                "language": "en",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Updated Name"
        assert data["phone"] == "555-1234"
        assert data["timezone"] == "America/New_York"
        assert data["language"] == "en"

        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me = me_resp.json()
        assert me["full_name"] == "Updated Name"
        assert me["phone"] == "555-1234"
        assert me["timezone"] == "America/New_York"
        assert me["language"] == "en"

    @pytest.mark.anyio
    async def test_admin_invalid_timezone_422(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"tz-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            "/api/v1/auth/profile",
            json={"timezone": "Not/AZone"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_client_updates_user_profile(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"cadm-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id, email="entity@test.com")
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"cu-{uuid.uuid4().hex[:8]}@test.com"
        )
        headers = await _client_auth_header(cu)

        resp = await client.patch(
            "/api/v1/client/auth/user-profile",
            json={"full_name": "Client New Name", "phone": "999-0000"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Client New Name"
        assert data["phone"] == "999-0000"

        me_resp = await client.get("/api/v1/client/auth/me", headers=headers)
        assert me_resp.status_code == 200
        me = me_resp.json()
        assert me["full_name"] == "Client New Name"
        assert me["phone"] == "999-0000"

        # Client ENTITY untouched (email/phone still original)
        admin_headers = await _admin_auth_header(admin)
        detail = await client.get(f"/api/v1/tenant/clients/{cli.id}", headers=admin_headers)
        assert detail.status_code == 200
        assert detail.json()["email"] == "entity@test.com"

    @pytest.mark.anyio
    async def test_profile_no_privilege_escalation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"esc-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            "/api/v1/auth/profile",
            json={"role": "super_admin"},
            headers=headers,
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Change password
# ═══════════════════════════════════════════════════════════════════════════


class TestChangePassword:
    @pytest.mark.anyio
    async def test_change_password_success(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"cp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": _TEST_PWD, "new_password": "newpass123!"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Old login fails
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": _TEST_PWD},
        )
        assert old_login.status_code == 401

        # New login works
        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": "newpass123!"},
        )
        assert new_login.status_code == 200

    @pytest.mark.anyio
    async def test_change_password_wrong_current_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"cpw-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrongcurrent", "new_password": "newpass123!"},
            headers=headers,
        )
        assert resp.status_code == 403
        assert "incorrect" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_client_change_password(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"ccp-{uuid.uuid4().hex[:8]}@test.com"
        )
        headers = await _client_auth_header(cu)

        resp = await client.post(
            "/api/v1/client/auth/change-password",
            json={"current_password": _TEST_PWD, "new_password": "newclient123!"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        old_login = await client.post(
            "/api/v1/client/auth/login",
            json={"email": cu.email, "password": _TEST_PWD},
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/api/v1/client/auth/login",
            json={"email": cu.email, "password": "newclient123!"},
        )
        assert new_login.status_code == 200

    @pytest.mark.anyio
    async def test_change_password_policy_enforced(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"cpp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _set_password_min_length(db_session, tenant.id, "14")
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": _TEST_PWD, "new_password": "tencharlen"},
            headers=headers,
        )
        assert resp.status_code == 422
        assert "14 characters" in resp.json()["error"]["message"]


# ═══════════════════════════════════════════════════════════════════════════
# Forgot password
# ═══════════════════════════════════════════════════════════════════════════


class TestForgotPassword:
    @pytest.mark.anyio
    async def test_admin_forgot_password_sends_email(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"fpa-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )

        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": admin.email},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        raw_token = _extract_raw_token_from_log(caplog, admin.email)
        assert raw_token is not None, "Raw token not found in log"

        new_password = "brandnew123!"
        consume = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": new_password},
        )
        assert consume.status_code == 200

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": new_password},
        )
        assert login.status_code == 200

    @pytest.mark.anyio
    async def test_admin_forgot_unknown_email_ok(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.anyio
    async def test_client_forgot_and_reset(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"fpc-{uuid.uuid4().hex[:8]}@test.com"
        )

        resp = await client.post(
            "/api/v1/client/auth/forgot-password",
            json={"email": cu.email},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        raw_token = _extract_raw_token_from_log(caplog, cu.email)
        assert raw_token is not None, "Raw token not found in log"

        new_password = "newclientpwd1!"
        reset = await client.post(
            "/api/v1/client/auth/reset-password",
            json={"token": raw_token, "new_password": new_password},
        )
        assert reset.status_code == 200
        assert reset.json()["status"] == "ok"

        login = await client.post(
            "/api/v1/client/auth/login",
            json={"email": cu.email, "password": new_password},
        )
        assert login.status_code == 200

        # Reused token -> 409
        reuse = await client.post(
            "/api/v1/client/auth/reset-password",
            json={"token": raw_token, "new_password": "anotherpwd123!"},
        )
        assert reuse.status_code == 409

    @pytest.mark.anyio
    async def test_client_reset_invalid_token_404(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/client/auth/reset-password",
            json={"token": "garbage_token", "new_password": "strongpwd123!"},
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Activity
# ═══════════════════════════════════════════════════════════════════════════


class TestActivity:
    @pytest.mark.anyio
    async def test_activity_records_password_and_profile(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"act-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": _TEST_PWD, "new_password": "newpass123!"},
            headers=headers,
        )
        await client.patch(
            "/api/v1/auth/profile",
            json={"phone": "555-9999"},
            headers=headers,
        )

        resp = await client.get("/api/v1/auth/activity", headers=headers)
        assert resp.status_code == 200
        entries = resp.json()
        event_types = {e["event_type"] for e in entries}
        assert "password.changed" in event_types
        assert "profile.updated" in event_types

        # Newest first
        created = [e["created_at"] for e in entries]
        assert created == sorted(created, reverse=True)

    @pytest.mark.anyio
    async def test_activity_only_own_rows(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"owna-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        admin_b = await _create_user(
            db_session, f"ownb-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers_a = await _admin_auth_header(admin_a)
        headers_b = await _admin_auth_header(admin_b)

        # Only admin_b changes its password
        await client.post(
            "/api/v1/auth/change-password",
            json={"current_password": _TEST_PWD, "new_password": "newpass123!"},
            headers=headers_b,
        )

        resp = await client.get("/api/v1/auth/activity", headers=headers_a)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_activity_read_only(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"ro-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/auth/activity", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        for entry in resp.json():
            assert set(entry.keys()) == {
                "id",
                "event_type",
                "description",
                "old_value",
                "new_value",
                "created_at",
            }

    @pytest.mark.anyio
    async def test_client_activity(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"cact-{uuid.uuid4().hex[:8]}@test.com"
        )
        headers = await _client_auth_header(cu)

        await client.post(
            "/api/v1/client/auth/change-password",
            json={"current_password": _TEST_PWD, "new_password": "newclient123!"},
            headers=headers,
        )

        resp = await client.get("/api/v1/client/auth/activity", headers=headers)
        assert resp.status_code == 200
        entries = resp.json()
        assert any(e["event_type"] == "password.changed" for e in entries)


# ═══════════════════════════════════════════════════════════════════════════
# Password policy wiring
# ═══════════════════════════════════════════════════════════════════════════


class TestPasswordPolicyWiring:
    @pytest.mark.anyio
    async def test_admin_reset_consume_policy(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"rp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        target = await _create_user(
            db_session, f"rpt-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.MANAGER, tenant.id
        )
        await _set_password_min_length(db_session, tenant.id, "14")
        headers = await _admin_auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        assert resp.status_code == 200
        raw_token = _extract_raw_token_from_log(caplog, target.email)
        assert raw_token is not None

        consume = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "tencharlen"},
        )
        assert consume.status_code == 422
        assert "14 characters" in consume.json()["error"]["message"]

    @pytest.mark.anyio
    async def test_client_register_policy_enforced(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"reg-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        await _set_password_min_length(db_session, tenant.id, "14")

        raw_token = "registerpolicytoken"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        inv = ClientInvite(
            tenant_id=tenant.id,
            client_id=cli.id,
            email=f"regpol-{uuid.uuid4().hex[:8]}@test.com",
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=3),
            invited_by=admin.id,
        )
        db_session.add(inv)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/client/auth/register",
            json={
                "token": raw_token,
                "full_name": "Policy Register",
                "password": "tencharlen",
            },
        )
        assert resp.status_code == 422
        assert "14 characters" in resp.json()["error"]["message"]


# ═══════════════════════════════════════════════════════════════════════════
# Notification preferences (TODO-116)
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationPreferences:
    @pytest.mark.anyio
    async def test_defaults_all_enabled(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"npref-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.get("/api/v1/auth/notification-preferences", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert [d["event_type"] for d in data] == [
            "new_comment",
            "invoice_issued",
            "payment_received",
            "milestone_completed",
        ]
        assert all(d["enabled"] is True for d in data)

    @pytest.mark.anyio
    async def test_disable_event(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"npref2-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)

        resp = await client.patch(
            "/api/v1/auth/notification-preferences",
            json={"preferences": [{"event_type": "new_comment", "enabled": False}]},
            headers=headers,
        )
        assert resp.status_code == 200
        by_type = {d["event_type"]: d["enabled"] for d in resp.json()}
        assert by_type["new_comment"] is False
        assert by_type["invoice_issued"] is True
        assert by_type["payment_received"] is True
        assert by_type["milestone_completed"] is True

        # Persisted
        get_resp = await client.get("/api/v1/auth/notification-preferences", headers=headers)
        assert get_resp.status_code == 200
        assert {d["event_type"]: d["enabled"] for d in get_resp.json()} == by_type

    @pytest.mark.anyio
    async def test_client_preferences_isolated(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"cnp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"cncu-{uuid.uuid4().hex[:8]}@test.com"
        )
        admin_headers = await _admin_auth_header(admin)
        client_headers = await _client_auth_header(cu)

        patch = await client.patch(
            "/api/v1/client/auth/notification-preferences",
            json={"preferences": [{"event_type": "invoice_issued", "enabled": False}]},
            headers=client_headers,
        )
        assert patch.status_code == 200

        admin_resp = await client.get(
            "/api/v1/auth/notification-preferences", headers=admin_headers
        )
        assert admin_resp.status_code == 200
        admin_by_type = {d["event_type"]: d["enabled"] for d in admin_resp.json()}
        assert admin_by_type["invoice_issued"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Preference-aware dispatch (TODO-108)
# ═══════════════════════════════════════════════════════════════════════════


class TestPrefsAwareDispatch:
    @pytest.mark.anyio
    async def test_disabled_new_comment_skips_email(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO, logger="app.services.email")
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"pda-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        admin_b = await _create_user(
            db_session, f"pdb-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"pdcu-{uuid.uuid4().hex[:8]}@client.com"
        )
        project = await _create_project(db_session, tenant.id, cli.id, owner_id=admin_a.id)

        # B opts out of new_comment notifications
        patch = await client.patch(
            "/api/v1/auth/notification-preferences",
            json={"preferences": [{"event_type": "new_comment", "enabled": False}]},
            headers=await _admin_auth_header(admin_b),
        )
        assert patch.status_code == 200

        caplog.clear()

        # A posts a shared comment
        resp = await client.post(
            f"/api/v1/tenant/projects/{project.id}/comments",
            json={"content": "shared note"},
            headers=await _admin_auth_header(admin_a),
        )
        assert resp.status_code == 201

        email_msgs = [r.getMessage() for r in caplog.records if "Email to=" in r.getMessage()]
        assert email_msgs, "no emails dispatched for shared comment"
        assert not any(
            f"Email to={admin_b.email}" in m for m in email_msgs
        ), "disabled admin was still emailed"
        assert any(
            f"Email to={cu.email}" in m for m in email_msgs
        ), "client user (default enabled) was not emailed"

    @pytest.mark.anyio
    async def test_enabled_recipient_gets_email(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO, logger="app.services.email")
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"pda2-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        admin_b = await _create_user(
            db_session, f"pdb2-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        cli = await _create_client(db_session, tenant.id)
        await _create_client_user(
            db_session, cli.id, tenant.id, f"pdcu2-{uuid.uuid4().hex[:8]}@client.com"
        )
        project = await _create_project(db_session, tenant.id, cli.id, owner_id=admin_a.id)

        caplog.clear()

        resp = await client.post(
            f"/api/v1/tenant/projects/{project.id}/comments",
            json={"content": "shared note"},
            headers=await _admin_auth_header(admin_a),
        )
        assert resp.status_code == 201

        email_msgs = [r.getMessage() for r in caplog.records if "Email to=" in r.getMessage()]
        assert any(
            f"Email to={admin_b.email}" in m for m in email_msgs
        ), "enabled admin was not emailed"


# ═══════════════════════════════════════════════════════════════════════════
# Email change + verification (TODO-110)
# ═══════════════════════════════════════════════════════════════════════════


class TestEmailChange:
    @pytest.mark.anyio
    async def test_admin_email_change_requires_verification(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"emc-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)
        new_email = f"new-{uuid.uuid4().hex[:8]}@example.com"

        resp = await client.patch(
            "/api/v1/auth/profile", json={"email": new_email}, headers=headers
        )
        assert resp.status_code == 200

        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        me_data = me.json()
        assert me_data["email"] == admin.email
        assert me_data["pending_email"] == new_email

        raw = _extract_raw_token_from_log(caplog, new_email)
        assert raw is not None, "verification link with token not found in log"

        # Old email stays active until verified
        old_login = await client.post(
            "/api/v1/auth/login", json={"email": admin.email, "password": _TEST_PWD}
        )
        assert old_login.status_code == 200

    @pytest.mark.anyio
    async def test_admin_verify_email(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"emv-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)
        old_email = admin.email
        new_email = f"vnew-{uuid.uuid4().hex[:8]}@example.com"

        await client.patch("/api/v1/auth/profile", json={"email": new_email}, headers=headers)
        raw = _extract_raw_token_from_log(caplog, new_email)
        assert raw is not None

        verify = await client.post("/api/v1/auth/verify-email", json={"token": raw})
        assert verify.status_code == 200
        assert verify.json()["status"] == "ok"

        me = await client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        me_data = me.json()
        assert me_data["email"] == new_email
        assert me_data["pending_email"] is None

        # New email logs in; old email does not
        new_login = await client.post(
            "/api/v1/auth/login", json={"email": new_email, "password": _TEST_PWD}
        )
        assert new_login.status_code == 200

        old_login = await client.post(
            "/api/v1/auth/login", json={"email": old_email, "password": _TEST_PWD}
        )
        assert old_login.status_code == 401

        # Token is single-use
        reuse = await client.post("/api/v1/auth/verify-email", json={"token": raw})
        assert reuse.status_code == 409

    @pytest.mark.anyio
    async def test_email_change_duplicate_409(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"dup-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        admin_b = await _create_user(
            db_session, f"dup2-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )

        resp = await client.patch(
            "/api/v1/auth/profile",
            json={"email": admin_b.email},
            headers=await _admin_auth_header(admin_a),
        )
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_verify_invalid_token_404(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/verify-email", json={"token": "garbage_token"})
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_client_email_change_flow(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        cli = await _create_client(db_session, tenant.id)
        cu = await _create_client_user(
            db_session, cli.id, tenant.id, f"cem-{uuid.uuid4().hex[:8]}@test.com"
        )
        headers = await _client_auth_header(cu)
        new_email = f"cnew-{uuid.uuid4().hex[:8]}@example.com"

        resp = await client.patch(
            "/api/v1/client/auth/user-profile", json={"email": new_email}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["pending_email"] == new_email

        raw = _extract_raw_token_from_log(caplog, new_email)
        assert raw is not None

        verify = await client.post("/api/v1/client/auth/verify-email", json={"token": raw})
        assert verify.status_code == 200
        assert verify.json()["status"] == "ok"

        new_login = await client.post(
            "/api/v1/client/auth/login", json={"email": new_email, "password": _TEST_PWD}
        )
        assert new_login.status_code == 200

    @pytest.mark.anyio
    async def test_email_change_activity(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        caplog.set_level(logging.INFO)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"ema-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _admin_auth_header(admin)
        old_email = admin.email
        new_email = f"act-{uuid.uuid4().hex[:8]}@example.com"

        await client.patch("/api/v1/auth/profile", json={"email": new_email}, headers=headers)
        raw = _extract_raw_token_from_log(caplog, new_email)
        assert raw is not None

        verify = await client.post("/api/v1/auth/verify-email", json={"token": raw})
        assert verify.status_code == 200

        resp = await client.get("/api/v1/auth/activity", headers=headers)
        assert resp.status_code == 200
        entries = resp.json()
        email_changed = [e for e in entries if e["event_type"] == "email.changed"]
        assert email_changed, "no email.changed activity entry"
        entry = email_changed[0]
        assert entry["old_value"] == old_email
        assert entry["new_value"] == new_email
