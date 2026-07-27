"""Integration tests for user administration endpoints (TODO-029..TODO-033)."""

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
from app.models.enums import AdminUserRole, TenantStatus
from app.models.password_reset_token import PasswordResetToken
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.services.users import LastAdminError, ensure_not_last_admin

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


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
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


# ── Test List Users ────────────────────────────────────────────────────────


class TestListUsers:
    """GET /api/v1/tenant/users"""

    @pytest.mark.anyio
    async def test_list_success(self, client: AsyncClient, db_session: AsyncSession):
        """200: list users paginated."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        emp = await _create_user(
            db_session, f"emp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, tenant.id
        )
        headers = await _auth_header(admin)

        resp = await client.get("/api/v1/tenant/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        emails = {u["email"] for u in data["items"]}
        assert admin.email in emails
        assert emp.email in emails

    @pytest.mark.anyio
    async def test_list_filter_active(self, client: AsyncClient, db_session: AsyncSession):
        """?is_active=true filters active only."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"act-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_user(
            db_session,
            f"inact-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
            is_active=False,
        )
        headers = await _auth_header(admin)

        resp = await client.get("/api/v1/tenant/users?is_active=true", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(u["is_active"] for u in data["items"])

    @pytest.mark.anyio
    async def test_list_filter_role(self, client: AsyncClient, db_session: AsyncSession):
        """?role=manager filters by role."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"rolefilt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        mgr = await _create_user(
            db_session, f"mgr-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.MANAGER, tenant.id
        )
        headers = await _auth_header(admin)

        resp = await client.get("/api/v1/tenant/users?role=manager", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(u["role"] == "manager" for u in data["items"])
        emails = {u["email"] for u in data["items"]}
        assert mgr.email in emails
        assert admin.email not in emails

    @pytest.mark.anyio
    async def test_list_tenant_isolation(self, client: AsyncClient, db_session: AsyncSession):
        """Tenant A cannot see Tenant B's users."""
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id)
        tenant_b = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"iso-a-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        user_b = await _create_user(
            db_session, f"iso-b-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant_b.id
        )
        headers_a = await _auth_header(admin_a)

        resp = await client.get("/api/v1/tenant/users", headers=headers_a)
        assert resp.status_code == 200
        emails = {u["email"] for u in resp.json()["items"]}
        assert admin_a.email in emails
        assert user_b.email not in emails

    @pytest.mark.anyio
    async def test_manager_can_list(self, client: AsyncClient, db_session: AsyncSession):
        """Manager has view admin_users -> 200."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        mgr = await _create_user(
            db_session,
            f"mgrlist-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        await _create_user(
            db_session, f"emp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, tenant.id
        )
        headers = await _auth_header(mgr)

        resp = await client.get("/api/v1/tenant/users", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    @pytest.mark.anyio
    async def test_employee_cannot_list(self, client: AsyncClient, db_session: AsyncSession):
        """Employee no view admin_users -> 403."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        emp = await _create_user(
            db_session,
            f"emplist-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(emp)

        resp = await client.get("/api/v1/tenant/users", headers=headers)
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        """No auth -> 401."""
        resp = await client.get("/api/v1/tenant/users")
        assert resp.status_code == 401


# ── Test Role Change ───────────────────────────────────────────────────────


class TestChangeRole:
    """PATCH /api/v1/tenant/users/{id}/role"""

    @pytest.mark.anyio
    async def test_role_change_success(self, client: AsyncClient, db_session: AsyncSession):
        """Happy path: role updated, audit logged."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        target = await _create_user(
            db_session,
            f"target-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(admin)

        resp = await client.patch(
            f"/api/v1/tenant/users/{target.id}/role",
            json={"role": "manager"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify DB
        await db_session.refresh(target)
        assert target.role == AdminUserRole.MANAGER

    @pytest.mark.anyio
    async def test_role_change_self_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cannot change own role -> 422."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"self-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)

        resp = await client.patch(
            f"/api/v1/tenant/users/{admin.id}/role",
            json={"role": "manager"},
            headers=headers,
        )
        assert resp.status_code == 422
        assert "own role" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_role_change_cross_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cross-tenant target -> 404 (no existence leak)."""
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id)
        tenant_b = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"cross-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant_a.id
        )
        user_b = await _create_user(
            db_session,
            f"userb-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant_b.id,
        )
        headers = await _auth_header(admin_a)

        resp = await client.patch(
            f"/api/v1/tenant/users/{user_b.id}/role",
            json={"role": "manager"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_role_change_last_admin_not_blocked_when_other_remains(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Changing one admin's role to manager ok when another admin remains."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"lastadm-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        other_admin = await _create_user(
            db_session,
            f"otheradm-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _auth_header(admin)

        resp = await client.patch(
            f"/api/v1/tenant/users/{other_admin.id}/role",
            json={"role": "manager"},
            headers=headers,
        )
        assert resp.status_code == 200
        await db_session.refresh(other_admin)
        assert other_admin.role == AdminUserRole.MANAGER

    @pytest.mark.anyio
    async def test_manager_cannot_change_role(self, client: AsyncClient, db_session: AsyncSession):
        """Manager -> 403."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        mgr = await _create_user(
            db_session,
            f"mgrrole-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        emp = await _create_user(
            db_session,
            f"emprole-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(mgr)

        resp = await client.patch(
            f"/api/v1/tenant/users/{emp.id}/role",
            json={"role": "manager"},
            headers=headers,
        )
        assert resp.status_code == 403


# ── Test Deactivate / Reactivate ───────────────────────────────────────────


class TestDeactivate:
    """POST /api/v1/tenant/users/{id}/deactivate"""

    @pytest.mark.anyio
    async def test_deactivate_success(self, client: AsyncClient, db_session: AsyncSession):
        """Happy path: is_active=false, login blocked after."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"deactadmin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        # Create another admin so last-admin guard doesn't fire
        await _create_user(
            db_session,
            f"otheradmin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"deacttarget-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{target.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 200

        # DB check
        await db_session.refresh(target)
        assert target.is_active is False

        # Login blocked
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": target.email, "password": _TEST_PWD},
        )
        assert login_resp.status_code == 401

    @pytest.mark.anyio
    async def test_deactivate_self_returns_422(self, client: AsyncClient, db_session: AsyncSession):
        """Cannot deactivate self -> 422."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"selfdeact-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{admin.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 422
        assert "yourself" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_deactivate_last_admin_when_other_admin_remains_ok(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Deactivating one admin succeeds when another admin remains."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"deactadm1-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        other_admin = await _create_user(
            db_session,
            f"deactadm2-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{other_admin.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 200
        await db_session.refresh(other_admin)
        assert other_admin.is_active is False

    @pytest.mark.anyio
    async def test_deactivate_already_inactive_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Already deactivated -> 409."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"alreadyd-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        # Create another admin for guard
        await _create_user(
            db_session, f"otherd-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        target = await _create_user(
            db_session,
            f"inactive-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
            is_active=False,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{target.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 409
        assert "already deactivated" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_reactivate_success(self, client: AsyncClient, db_session: AsyncSession):
        """Reactivate restores login."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"reactadmin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"reacttarget-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
            is_active=False,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{target.id}/reactivate",
            headers=headers,
        )
        assert resp.status_code == 200

        await db_session.refresh(target)
        assert target.is_active is True

        # Login works again
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": target.email, "password": _TEST_PWD},
        )
        assert login_resp.status_code == 200

    @pytest.mark.anyio
    async def test_reactivate_already_active_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Already active -> 409."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"already-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{admin.id}/reactivate",
            headers=headers,
        )
        assert resp.status_code == 409
        assert "already active" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_deactivate_cross_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cross-tenant -> 404."""
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id)
        tenant_b = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session,
            f"crossd-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant_a.id,
        )
        user_b = await _create_user(
            db_session,
            f"userbd-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant_b.id,
        )
        headers = await _auth_header(admin_a)

        resp = await client.post(
            f"/api/v1/tenant/users/{user_b.id}/deactivate",
            headers=headers,
        )
        assert resp.status_code == 404


# ── Test Admin-Triggered Password Reset ─────────────────────────────────────


class TestAdminResetPassword:
    """POST /api/v1/tenant/users/{id}/reset-password"""

    @pytest.mark.anyio
    async def test_initiate_reset_success(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        """200: token created, email sent, audit logged."""
        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"resetadm-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"resettgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Raw token in console email log
        raw_token = _extract_raw_token_from_log(caplog, target.email)
        assert raw_token is not None, "Raw token not found in log"
        assert (
            "initiated a password reset"
            in [r.getMessage() for r in caplog.records if target.email in r.getMessage()][0]
        )

        # Token in DB
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        from sqlalchemy import select

        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        result = await db_session.execute(stmt)
        token_obj = result.scalar_one_or_none()
        assert token_obj is not None
        assert token_obj.user_id == target.id
        assert token_obj.used_at is None
        assert token_obj.expires_at > datetime.now(UTC)

    @pytest.mark.anyio
    async def test_initiate_reset_invalidates_old_tokens(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        """Re-initiate invalidates previous unused tokens."""
        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"invaladm-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"invaltgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        headers = await _auth_header(admin)

        # First reset
        resp1 = await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        assert resp1.status_code == 200
        raw1 = _extract_raw_token_from_log(caplog, target.email)
        assert raw1 is not None
        caplog.clear()

        # Second reset
        resp2 = await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        assert resp2.status_code == 200

        # First token should be marked used
        hash1 = hashlib.sha256(raw1.encode()).hexdigest()
        from sqlalchemy import select

        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == hash1)
        result = await db_session.execute(stmt)
        old_token = result.scalar_one_or_none()
        assert old_token is not None
        assert old_token.used_at is not None

    @pytest.mark.anyio
    async def test_initiate_reset_deactivated_user_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Deactivated user -> 422."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"deactadm-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"deacttgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
            is_active=False,
        )
        headers = await _auth_header(admin)

        resp = await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        assert resp.status_code == 422
        assert "deactivated" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_initiate_reset_cross_tenant_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Cross-tenant -> 404."""
        plan = await _create_plan(db_session)
        tenant_a = await _create_tenant(db_session, plan.id)
        tenant_b = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session,
            f"crossra-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant_a.id,
        )
        user_b = await _create_user(
            db_session,
            f"crossrb-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant_b.id,
        )
        headers = await _auth_header(admin_a)

        resp = await client.post(
            f"/api/v1/tenant/users/{user_b.id}/reset-password",
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_manager_cannot_initiate_reset(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Manager -> 403."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        mgr = await _create_user(
            db_session, f"mgrr-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.MANAGER, tenant.id
        )
        emp = await _create_user(
            db_session, f"empr-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, tenant.id
        )
        headers = await _auth_header(mgr)

        resp = await client.post(
            f"/api/v1/tenant/users/{emp.id}/reset-password",
            headers=headers,
        )
        assert resp.status_code == 403


# ── Test Public Consume Password Reset ─────────────────────────────────────


class TestConsumePasswordReset:
    """POST /api/v1/auth/reset-password"""

    @pytest.mark.anyio
    async def test_consume_success(self, client: AsyncClient, db_session: AsyncSession, caplog):
        """Happy path: new password works, old password doesn't."""
        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"consadm-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        target = await _create_user(
            db_session,
            f"constgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        headers = await _auth_header(admin)

        # Initiate reset
        await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        raw_token = _extract_raw_token_from_log(caplog, target.email)
        assert raw_token is not None

        new_password = "newstrongpwd123!"
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": new_password},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # New password works
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": target.email, "password": new_password},
        )
        assert login_resp.status_code == 200

        # Old password fails
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": target.email, "password": _TEST_PWD},
        )
        assert old_login.status_code == 401

    @pytest.mark.anyio
    async def test_consume_unknown_token_returns_404(self, client: AsyncClient):
        """Unknown token -> 404."""
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "unknown_token_here", "new_password": "strongpwd123!"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOT_FOUND"

    @pytest.mark.anyio
    async def test_consume_expired_token_returns_410(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Expired token -> 410."""
        # Create an expired token directly
        target = await _create_user(
            db_session, f"exptgt-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, None
        )
        raw = "expiredtoken123"
        thash = hashlib.sha256(raw.encode()).hexdigest()
        t = PasswordResetToken(
            user_id=target.id,
            token_hash=thash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            created_by=target.id,
        )
        db_session.add(t)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw, "new_password": "strongpwd123!"},
        )
        assert resp.status_code == 410
        assert "expired" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_consume_used_token_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Already used token -> 409."""
        target = await _create_user(
            db_session, f"usedtgt-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, None
        )
        raw = "usedtoken456"
        thash = hashlib.sha256(raw.encode()).hexdigest()
        t = PasswordResetToken(
            user_id=target.id,
            token_hash=thash,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            used_at=datetime.now(UTC),
            created_by=target.id,
        )
        db_session.add(t)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw, "new_password": "strongpwd123!"},
        )
        assert resp.status_code == 409
        assert "already been used" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_consume_short_password_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """New password < 10 chars -> 422."""
        target = await _create_user(
            db_session, f"shorttgt-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, None
        )
        raw = "shortpwtest"
        thash = hashlib.sha256(raw.encode()).hexdigest()
        t = PasswordResetToken(
            user_id=target.id,
            token_hash=thash,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
            created_by=target.id,
        )
        db_session.add(t)
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw, "new_password": "short"},
        )
        assert resp.status_code == 422
        assert "10 characters" in resp.json()["error"]["message"]


# ── Test Audit Entries ─────────────────────────────────────────────────────


class TestAuditEntries:
    """Verify audit log entries are created for sensitive actions."""

    @pytest.mark.anyio
    async def test_role_change_audit(self, client: AsyncClient, db_session: AsyncSession):
        from app.models.audit_log import AuditLog

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"audadm-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        target = await _create_user(
            db_session,
            f"audtgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(admin)

        await client.patch(
            f"/api/v1/tenant/users/{target.id}/role",
            json={"role": "manager"},
            headers=headers,
        )

        # Check audit logs
        from sqlalchemy import select

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "user.role_changed",
                AuditLog.entity_id == str(target.id),
            )
            .order_by(AuditLog.created_at.desc())
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_id == admin.id
        assert entry.details["from"] == "employee"
        assert entry.details["to"] == "manager"

    @pytest.mark.anyio
    async def test_deactivate_audit(self, client: AsyncClient, db_session: AsyncSession):
        from app.models.audit_log import AuditLog

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"auddeact-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        await _create_user(
            db_session,
            f"audotheradmin-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"auddeacttgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
        )
        headers = await _auth_header(admin)

        await client.post(
            f"/api/v1/tenant/users/{target.id}/deactivate",
            headers=headers,
        )

        from sqlalchemy import select

        stmt = select(AuditLog).where(
            AuditLog.action == "user.deactivated",
            AuditLog.entity_id == str(target.id),
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_id == admin.id

    @pytest.mark.anyio
    async def test_reactivate_audit(self, client: AsyncClient, db_session: AsyncSession):
        from app.models.audit_log import AuditLog

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"audreact-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"audreacttgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.EMPLOYEE,
            tenant.id,
            is_active=False,
        )
        headers = await _auth_header(admin)

        await client.post(
            f"/api/v1/tenant/users/{target.id}/reactivate",
            headers=headers,
        )

        from sqlalchemy import select

        stmt = select(AuditLog).where(
            AuditLog.action == "user.reactivated",
            AuditLog.entity_id == str(target.id),
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_id == admin.id

    @pytest.mark.anyio
    async def test_reset_initiated_audit(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        from app.models.audit_log import AuditLog

        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"audreset-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        target = await _create_user(
            db_session,
            f"audresettgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        headers = await _auth_header(admin)

        await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )

        from sqlalchemy import select

        stmt = select(AuditLog).where(
            AuditLog.action == "user.password_reset_initiated",
            AuditLog.entity_id == str(target.id),
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_id == admin.id

    @pytest.mark.anyio
    async def test_reset_completed_audit(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        from app.models.audit_log import AuditLog

        caplog.set_level(logging.INFO)

        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"audcomp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        target = await _create_user(
            db_session,
            f"audcomptgt-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.MANAGER,
            tenant.id,
        )
        headers = await _auth_header(admin)

        await client.post(
            f"/api/v1/tenant/users/{target.id}/reset-password",
            headers=headers,
        )
        raw_token = _extract_raw_token_from_log(caplog, target.email)
        assert raw_token is not None

        await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "newstrong123!!"},
        )

        from sqlalchemy import select

        stmt = (
            select(AuditLog)
            .where(
                AuditLog.action == "user.password_reset_completed",
                AuditLog.entity_id == str(target.id),
            )
            .order_by(AuditLog.created_at.desc())
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_id == target.id


# ── Test Last-Admin Guard Service ──────────────────────────────────────────


class TestEnsureNotLastAdmin:
    """Direct unit tests for ensure_not_last_admin guard."""

    @pytest.mark.anyio
    async def test_raises_when_only_admin(self, db_session: AsyncSession):
        """Raises LastAdminError when target is the only active admin."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"only-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )

        with pytest.raises(LastAdminError) as exc:
            await ensure_not_last_admin(db_session, tenant.id, admin.id)
        assert "last active admin" in str(exc.value).lower()

    @pytest.mark.anyio
    async def test_passes_when_other_admin_exists(self, db_session: AsyncSession):
        """Passes when another active admin exists in the tenant."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin_a = await _create_user(
            db_session, f"a-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_user(
            db_session, f"b-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )

        # Should not raise
        await ensure_not_last_admin(db_session, tenant.id, admin_a.id)

    @pytest.mark.anyio
    async def test_ignores_non_admin_roles(self, db_session: AsyncSession):
        """Only counts Admin role, ignores managers/employees."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"ign-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_user(
            db_session, f"mgr-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.MANAGER, tenant.id
        )
        await _create_user(
            db_session, f"emp-{uuid.uuid4().hex[:8]}@testco.com", AdminUserRole.EMPLOYEE, tenant.id
        )

        with pytest.raises(LastAdminError):
            await ensure_not_last_admin(db_session, tenant.id, admin.id)

    @pytest.mark.anyio
    async def test_ignores_inactive_admins(self, db_session: AsyncSession):
        """Inactive admins not counted."""
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session,
            f"inactadm-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )
        await _create_user(
            db_session,
            f"inactadm2-{uuid.uuid4().hex[:8]}@testco.com",
            AdminUserRole.ADMIN,
            tenant.id,
            is_active=False,
        )

        with pytest.raises(LastAdminError):
            await ensure_not_last_admin(db_session, tenant.id, admin.id)
