"""Integration tests for RBAC dependency enforcement.

Tests that require_permission and require_roles work via a throwaway
endpoint, and that role changes take effect next request.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import require_permission, require_roles
from app.core.errors import register_error_handlers
from app.core.security import create_access_token, hash_password
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import AdminUserRole
from app.models.plan import Plan
from app.models.tenant import Tenant

_TEST_PWD = "rbactest123!"


def _make_app():
    app = FastAPI()
    register_error_handlers(app)
    router = APIRouter(prefix="/test")

    @router.get("/manage-clients")
    async def _manage_clients(_=Depends(require_permission("manage", "clients"))):
        return {"ok": True}

    @router.get("/require-admin")
    async def _require_admin(_=Depends(require_roles(AdminUserRole.ADMIN))):
        return {"ok": True}

    @router.get("/require-super-admin")
    async def _require_su(
        _=Depends(require_roles(AdminUserRole.SUPER_ADMIN)),
    ):
        return {"ok": True}

    app.include_router(router)
    return app


@pytest.fixture
def rbac_app():
    return _make_app()


@pytest.mark.anyio
async def test_require_permission_allows(db_session, session):
    """Manager can manage clients."""
    app = _make_app()

    async def _override_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)

    plan = Plan(
        name="RBACTest",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(
        business_name="RBAC",
        slug=f"rbac-{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
    )
    db_session.add(tenant)
    await db_session.commit()

    user = AdminUser(
        tenant_id=tenant.id,
        email="manager@rbac.com",
        full_name="Manager",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.MANAGER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role.value,
        realm="admin",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/test/manage-clients",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}


@pytest.mark.anyio
async def test_require_permission_denies(db_session, session):
    """Employee cannot manage clients."""
    app = _make_app()

    async def _override_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)

    plan = Plan(
        name="RBACDeny",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(
        business_name="RBACDeny",
        slug=f"rbac-deny-{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
    )
    db_session.add(tenant)
    await db_session.commit()

    user = AdminUser(
        tenant_id=tenant.id,
        email="emp@rbac.com",
        full_name="Employee",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.EMPLOYEE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role.value,
        realm="admin",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/test/manage-clients",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403, resp.text
        data = resp.json()
        assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.anyio
async def test_role_change_takes_effect_next_request(db_session, session):
    """Employee promoted to manager gets access on next request (no cache)."""
    app = _make_app()

    async def _override_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)

    plan = Plan(
        name="RoleChange",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(
        business_name="RoleChg",
        slug=f"rolechg-{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
    )
    db_session.add(tenant)
    await db_session.commit()

    user = AdminUser(
        tenant_id=tenant.id,
        email="promote@rbac.com",
        full_name="Promotee",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.EMPLOYEE,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Token issued as EMPLOYEE
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role.value,
        realm="admin",
    )

    # First request: EMPLOYEE cannot manage clients -> 403
    async with AsyncClient(transport=transport, base_url="http://test") as ac1:
        resp1 = await ac1.get(
            "/test/manage-clients",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp1.status_code == 403

    # Promote to MANAGER in DB
    user.role = AdminUserRole.MANAGER
    await db_session.commit()

    # Second request (same token, role reloaded from DB) -> 200
    async with AsyncClient(transport=transport, base_url="http://test") as ac2:
        resp2 = await ac2.get(
            "/test/manage-clients",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json() == {"ok": True}


@pytest.mark.anyio
async def test_deactivated_user_rejected_by_dependency(db_session, session):
    """Deactivated user gets 401 even with valid token."""
    app = _make_app()

    async def _override_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)

    plan = Plan(
        name="DeactTest",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=256,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(
        business_name="Deact",
        slug=f"deact-{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
    )
    db_session.add(tenant)
    await db_session.commit()

    user = AdminUser(
        tenant_id=tenant.id,
        email="deact@test.com",
        full_name="Deact",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.ADMIN,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role.value,
        realm="admin",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/test/manage-clients",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 401
