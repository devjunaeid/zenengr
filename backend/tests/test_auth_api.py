"""Integration tests for auth endpoints (login, me)."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.enums import AdminUserRole, TenantStatus
from app.models.plan import Plan
from app.models.tenant import Tenant

_TEST_PWD = "testpass123!"


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


class TestLogin:
    async def _login(self, client: AsyncClient, email: str, password: str = _TEST_PWD):
        return await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

    @pytest.mark.anyio
    async def test_login_success_tenant_admin(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        await _create_user(db_session, "admin@testco.com", AdminUserRole.ADMIN, tenant.id)

        resp = await self._login(client, "admin@testco.com")
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "admin@testco.com"
        assert data["user"]["role"] == "admin"
        assert data["user"]["tenant_id"] == str(tenant.id)

    @pytest.mark.anyio
    async def test_login_super_admin_no_tenant(self, client: AsyncClient, db_session: AsyncSession):
        await _create_user(db_session, "super@zenengr.dev", AdminUserRole.SUPER_ADMIN, None)

        resp = await self._login(client, "super@zenengr.dev")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["role"] == "super_admin"
        assert data["user"]["tenant_id"] is None

    @pytest.mark.anyio
    async def test_login_bad_password(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        await _create_user(db_session, "user@testco.com", AdminUserRole.ADMIN, tenant.id)

        resp = await self._login(client, "user@testco.com", "wrongpassword")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"
        assert data["error"]["message"] == "Invalid credentials"

    @pytest.mark.anyio
    async def test_login_unknown_email(self, client: AsyncClient, db_session: AsyncSession):
        resp = await self._login(client, "nobody@example.com")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["message"] == "Invalid credentials"

    @pytest.mark.anyio
    async def test_login_deactivated_user(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        await _create_user(
            db_session, "deactivated@testco.com", AdminUserRole.ADMIN, tenant.id, is_active=False
        )

        resp = await self._login(client, "deactivated@testco.com")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_login_suspended_tenant(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.SUSPENDED)
        await _create_user(db_session, "user@suspended.com", AdminUserRole.ADMIN, tenant.id)

        resp = await self._login(client, "user@suspended.com")
        assert resp.status_code == 403
        data = resp.json()
        assert "suspended" in data["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_login_cancelled_tenant(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.CANCELLED)
        await _create_user(db_session, "user@cancelled.com", AdminUserRole.ADMIN, tenant.id)

        resp = await self._login(client, "user@cancelled.com")
        assert resp.status_code == 403
        data = resp.json()
        assert "cancelled" in data["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_login_trial_tenant_ok(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, TenantStatus.TRIAL)
        await _create_user(db_session, "user@trial.com", AdminUserRole.ADMIN, tenant.id)

        resp = await self._login(client, "user@trial.com")
        assert resp.status_code == 200


class TestMe:
    @pytest.mark.anyio
    async def test_me_with_token(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        user = await _create_user(db_session, "whoami@testco.com", AdminUserRole.MANAGER, tenant.id)

        token = create_access_token(
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            role=user.role.value,
            realm="admin",
        )

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "whoami@testco.com"
        assert data["role"] == "manager"

    @pytest.mark.anyio
    async def test_me_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    @pytest.mark.anyio
    async def test_me_bad_token(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_me_wrong_realm(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        user = await _create_user(db_session, "client@testco.com", AdminUserRole.ADMIN, tenant.id)

        token = create_access_token(
            user_id=str(user.id),
            tenant_id=str(tenant.id),
            role=user.role.value,
            realm="client",  # wrong realm
        )

        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
