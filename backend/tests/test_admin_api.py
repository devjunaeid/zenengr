"""Integration tests for Super Admin platform APIs (TODO-005..008, 012, 015)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.enums import AdminUserRole, BillingCycle, SubscriptionStatus, TenantStatus
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.models.tenant_setting import TenantSetting
from app.models.tenant_subscription import TenantSubscription

_TEST_PWD = "testpass123!"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_plan(session: AsyncSession, name: str | None = None) -> Plan:
    plan = Plan(
        name=name or f"TestPlan-{uuid.uuid4().hex[:8]}",
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
    session: AsyncSession,
    plan_id: uuid.UUID,
    status: TenantStatus = TenantStatus.ACTIVE,
    slug: str | None = None,
    *,
    with_subscription: bool = True,
) -> Tenant:
    tenant = Tenant(
        business_name="TestCo",
        slug=slug or f"testco-{uuid.uuid4().hex[:8]}",
        status=status,
        plan_id=plan_id,
    )
    session.add(tenant)
    await session.flush()

    if with_subscription:
        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE
            if status != TenantStatus.TRIAL
            else SubscriptionStatus.TRIALING,
            billing_cycle=BillingCycle.MONTHLY,
        )
        session.add(sub)

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


# ═══════════════════════════════════════════════════════════════════════════
# Auth isolation
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthIsolation:
    """All admin endpoints require super_admin; others get 401/403."""

    @pytest.mark.anyio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/plans")
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_tenant_admin_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        admin = await _create_user(
            db_session, f"admin-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.ADMIN, tenant.id
        )
        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/admin/plans", headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "super admin" in data["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_manager_returns_403(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id)
        mgr = await _create_user(
            db_session, f"mgr-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.MANAGER, tenant.id
        )
        headers = await _auth_header(mgr)
        resp = await client.get("/api/v1/admin/plans", headers=headers)
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# Plans CRUD
# ═══════════════════════════════════════════════════════════════════════════


class TestPlansCRUD:
    """POST/GET/GET ID/PATCH/DELETE /api/v1/admin/plans"""

    @pytest.mark.anyio
    async def test_create_plan(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)

        resp = await client.post(
            "/api/v1/admin/plans",
            json={
                "name": "Pro",
                "description": "Professional plan",
                "max_admin_users": 10,
                "max_clients": 50,
                "max_active_projects": 20,
                "max_storage_mb": 1024,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Pro"
        assert data["max_admin_users"] == 10
        assert data["is_active"] is True
        assert "id" in data
        assert "tenant_count" in data

        # Verify DB
        from sqlalchemy import select

        stmt = select(Plan).where(Plan.name == "Pro")
        result = await db_session.execute(stmt)
        plan = result.scalar_one_or_none()
        assert plan is not None
        assert plan.max_clients == 50

    @pytest.mark.anyio
    async def test_create_plan_duplicate_name_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        await _create_plan(db_session, "Duplicate")

        resp = await client.post(
            "/api/v1/admin/plans",
            json={
                "name": "Duplicate",
                "max_admin_users": 5,
                "max_clients": 10,
                "max_active_projects": 5,
                "max_storage_mb": 256,
            },
            headers=headers,
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_list_plans(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        await _create_plan(db_session, "Alpha")
        await _create_plan(db_session, "Beta")

        resp = await client.get("/api/v1/admin/plans", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        names = [p["name"] for p in data]
        assert "Alpha" in names
        assert "Beta" in names

    @pytest.mark.anyio
    async def test_get_plan(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "Target")

        resp = await client.get(f"/api/v1/admin/plans/{plan.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Target"
        assert data["id"] == str(plan.id)

    @pytest.mark.anyio
    async def test_get_plan_not_found_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        fake_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/admin/plans/{fake_id}", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_plan(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "UpdateMe")

        resp = await client.patch(
            f"/api/v1/admin/plans/{plan.id}",
            json={"name": "Updated", "max_admin_users": 20},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["max_admin_users"] == 20

    @pytest.mark.anyio
    async def test_delete_plan_no_tenants(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "DeleteMe")

        resp = await client.delete(f"/api/v1/admin/plans/{plan.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        # Verify hard deleted
        stmt = select(Plan).where(Plan.id == plan.id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    @pytest.mark.anyio
    async def test_delete_plan_with_tenants_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "HasTenants")
        await _create_tenant(db_session, plan.id)

        resp = await client.delete(f"/api/v1/admin/plans/{plan.id}", headers=headers)
        assert resp.status_code == 409
        assert "assigned tenant" in resp.json()["error"]["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Create
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantCreate:
    """POST /api/v1/admin/tenants"""

    @pytest.mark.anyio
    async def test_create_tenant_happy_path(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "Starter")

        slug = f"acme-{uuid.uuid4().hex[:8]}"
        email = f"admin-{uuid.uuid4().hex[:8]}@acme.com"
        resp = await client.post(
            "/api/v1/admin/tenants",
            json={
                "business_name": "Acme Studio",
                "slug": slug,
                "plan_id": str(plan.id),
                "admin_email": email,
                "admin_full_name": "Alice Admin",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["business_name"] == "Acme Studio"
        assert data["slug"] == slug
        assert data["status"] == "trial"
        assert data["admin_email"] == email
        assert "temp_password" in data
        assert len(data["temp_password"]) > 0

        tenant_id = uuid.UUID(data["id"])

        # 1. Tenant exists
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await db_session.execute(stmt)
        tenant = result.scalar_one_or_none()
        assert tenant is not None
        assert tenant.status == TenantStatus.TRIAL

        # 2. Subscription exists
        stmt = select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
        result = await db_session.execute(stmt)
        sub = result.scalar_one_or_none()
        assert sub is not None
        assert sub.status == SubscriptionStatus.TRIALING
        assert sub.plan_id == plan.id

        # 3. Settings seeded
        stmt = select(TenantSetting).where(TenantSetting.tenant_id == tenant_id)
        result = await db_session.execute(stmt)
        settings = result.scalars().all()
        assert len(settings) >= 4

        # 4. Admin user exists
        stmt = select(AdminUser).where(AdminUser.email == email)
        result = await db_session.execute(stmt)
        admin = result.scalar_one_or_none()
        assert admin is not None
        assert admin.tenant_id == tenant_id
        assert admin.role == AdminUserRole.ADMIN

        # 5. Temp password works on login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": data["temp_password"]},
        )
        assert login_resp.status_code == 200
        assert login_resp.json()["user"]["email"] == email

    @pytest.mark.anyio
    async def test_create_tenant_invalid_slug_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)

        # Invalid: leading hyphen, uppercase, double hyphens
        for bad_slug in ["-bad", "BAD", "bad--slug", "bad-", "has space"]:
            resp = await client.post(
                "/api/v1/admin/tenants",
                json={
                    "business_name": "Bad Slug",
                    "slug": bad_slug,
                    "plan_id": str(plan.id),
                    "admin_email": "admin@bad.com",
                    "admin_full_name": "Bad Admin",
                },
                headers=headers,
            )
            assert resp.status_code == 422, f"Slug '{bad_slug}' should be invalid"

    @pytest.mark.anyio
    async def test_create_tenant_duplicate_slug_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        slug = f"dupe-{uuid.uuid4().hex[:8]}"
        await _create_tenant(db_session, plan.id, slug=slug)

        resp = await client.post(
            "/api/v1/admin/tenants",
            json={
                "business_name": "Duplicate",
                "slug": slug,
                "plan_id": str(plan.id),
                "admin_email": "admin@dupe.com",
                "admin_full_name": "Dupe Admin",
            },
            headers=headers,
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["error"]["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Slug Availability
# ═══════════════════════════════════════════════════════════════════════════


class TestSlugAvailable:
    """GET /api/v1/admin/tenants/slug-available"""

    @pytest.mark.anyio
    async def test_slug_valid_and_free(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)

        resp = await client.get(
            "/api/v1/admin/tenants/slug-available?slug=my-tenant", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "my-tenant"
        assert data["valid"] is True
        assert data["available"] is True

    @pytest.mark.anyio
    async def test_slug_valid_but_taken(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        slug = f"taken-{uuid.uuid4().hex[:8]}"
        await _create_tenant(db_session, plan.id, slug=slug)

        resp = await client.get(
            f"/api/v1/admin/tenants/slug-available?slug={slug}", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["available"] is False

    @pytest.mark.anyio
    async def test_slug_invalid(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)

        resp = await client.get("/api/v1/admin/tenants/slug-available?slug=-BAD-", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert data["available"] is False


# ═══════════════════════════════════════════════════════════════════════════
# Tenant List
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantList:
    """GET /api/v1/admin/tenants"""

    @pytest.mark.anyio
    async def test_list_paginated(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        t1 = await _create_tenant(db_session, plan.id, slug=f"list-{uuid.uuid4().hex[:8]}")
        t2 = await _create_tenant(db_session, plan.id, slug=f"list-{uuid.uuid4().hex[:8]}")

        resp = await client.get("/api/v1/admin/tenants", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        slugs = {t["slug"] for t in data["items"]}
        assert t1.slug in slugs
        assert t2.slug in slugs

    @pytest.mark.anyio
    async def test_list_filter_status(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        await _create_tenant(
            db_session, plan.id, TenantStatus.TRIAL, slug=f"trial-{uuid.uuid4().hex[:8]}"
        )
        await _create_tenant(
            db_session, plan.id, TenantStatus.ACTIVE, slug=f"act-{uuid.uuid4().hex[:8]}"
        )

        resp = await client.get("/api/v1/admin/tenants?status=trial", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["status"] == "trial" for t in data["items"])

    @pytest.mark.anyio
    async def test_list_search_q(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        await _create_tenant(
            db_session, plan.id, slug=f"searchme-{uuid.uuid4().hex[:8]}", status=TenantStatus.TRIAL
        )

        resp = await client.get("/api/v1/admin/tenants?q=searchme", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.anyio
    async def test_list_sort(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        await _create_tenant(db_session, plan.id, slug=f"sort-{uuid.uuid4().hex[:8]}")

        resp = await client.get("/api/v1/admin/tenants?sort=-created_at", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) > 0

    @pytest.mark.anyio
    async def test_list_has_plan_name_and_user_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "Gold")
        tenant = await _create_tenant(db_session, plan.id, slug=f"gold-{uuid.uuid4().hex[:8]}")
        await _create_user(
            db_session, f"u1-{uuid.uuid4().hex[:8]}@gold.com", AdminUserRole.ADMIN, tenant.id
        )
        await _create_user(
            db_session, f"u2-{uuid.uuid4().hex[:8]}@gold.com", AdminUserRole.MANAGER, tenant.id
        )

        resp = await client.get("/api/v1/admin/tenants", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        match = [t for t in data["items"] if t["slug"] == tenant.slug]
        assert len(match) == 1
        assert match[0]["plan_name"] == "Gold"
        assert match[0]["active_user_count"] >= 2
        # No operational data exposed
        assert "clients" not in match[0]
        assert "projects" not in match[0]


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Detail
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantDetail:
    """GET /api/v1/admin/tenants/{id}"""

    @pytest.mark.anyio
    async def test_get_detail(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "DetailPlan")
        tenant = await _create_tenant(db_session, plan.id, slug=f"detail-{uuid.uuid4().hex[:8]}")

        resp = await client.get(f"/api/v1/admin/tenants/{tenant.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["business_name"] == "TestCo"
        assert data["slug"] == tenant.slug
        assert data["plan_name"] == "DetailPlan"
        assert "subscription" in data
        assert "settings" in data

    @pytest.mark.anyio
    async def test_get_detail_not_found_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        resp = await client.get(f"/api/v1/admin/tenants/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Update
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantUpdate:
    """PATCH /api/v1/admin/tenants/{id}"""

    @pytest.mark.anyio
    async def test_update_fields(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, slug=f"upd-{uuid.uuid4().hex[:8]}")

        resp = await client.patch(
            f"/api/v1/admin/tenants/{tenant.id}",
            json={"business_name": "UpdatedCo", "logo_url": "https://example.com/logo.png"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["business_name"] == "UpdatedCo"
        assert data["logo_url"] == "https://example.com/logo.png"
        assert data["slug"] == tenant.slug  # unchanged

    @pytest.mark.anyio
    async def test_update_not_found_404(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        resp = await client.patch(
            f"/api/v1/admin/tenants/{uuid.uuid4()}",
            json={"business_name": "Nope"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_persists_across_sessions(self, app: Any):
        """PATCH /api/v1/admin/tenants/{id} must COMMIT: business_name
        survives a fresh DB session.

        Regression for the persistence bug where update_tenant flushed
        (via the repository) but never committed.
        """
        from httpx import ASGITransport
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from app.core.config import get_settings
        from app.db.session import get_session

        test_url = get_settings().database_url.rsplit("/", 1)[0] + "/app_test"
        engine = create_async_engine(test_url)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

            async with maker() as write_session:
                sa = await _create_user(
                    write_session,
                    f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev",
                    AdminUserRole.SUPER_ADMIN,
                    None,
                )
                headers = await _auth_header(sa)
                plan = await _create_plan(write_session)
                tenant = await _create_tenant(write_session, plan.id)

                async def _override_session():
                    yield write_session

                app.dependency_overrides[get_session] = _override_session
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    resp = await ac.patch(
                        f"/api/v1/admin/tenants/{tenant.id}",
                        json={"business_name": "SA-PersistedCo"},
                        headers=headers,
                    )
                    assert resp.status_code == 200
                    assert resp.json()["business_name"] == "SA-PersistedCo"

                # Write session closed; the service must have committed.
                # A brand-new session on the test engine must see the row.
                async with maker() as fresh:
                    stmt = select(Tenant).where(Tenant.id == tenant.id)
                    result = await fresh.execute(stmt)
                    fresh_tenant = result.scalar_one()
                    assert fresh_tenant.business_name == "SA-PersistedCo"

                    # The audit row written by the service must also be
                    # committed: a fresh session must see it too.
                    stmt = select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.action == "tenant.updated",
                    )
                    result = await fresh.execute(stmt)
                    entry = result.scalar_one_or_none()
                    assert entry is not None
                    assert "business_name" in entry.details.get("updated_fields", [])
        finally:
            await engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Lifecycle
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantLifecycle:
    """suspend, reactivate, cancel — POST endpoints"""

    @pytest.mark.anyio
    async def test_suspend_reactivate_cycle(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.TRIAL, slug=f"life-{uuid.uuid4().hex[:8]}"
        )
        await _create_user(
            db_session, f"lifeadmin-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.ADMIN, tenant.id
        )

        # Suspend
        resp = await client.post(f"/api/v1/admin/tenants/{tenant.id}/suspend", headers=headers)
        assert resp.status_code == 200
        await db_session.refresh(tenant)
        assert tenant.status == TenantStatus.SUSPENDED

        # Reactivate
        resp = await client.post(f"/api/v1/admin/tenants/{tenant.id}/reactivate", headers=headers)
        assert resp.status_code == 200
        await db_session.refresh(tenant)
        assert tenant.status == TenantStatus.ACTIVE

    @pytest.mark.anyio
    async def test_suspend_idempotent(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.SUSPENDED, slug=f"idemp-{uuid.uuid4().hex[:8]}"
        )

        resp = await client.post(f"/api/v1/admin/tenants/{tenant.id}/suspend", headers=headers)
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_suspend_cancelled_409(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.CANCELLED, slug=f"cantsus-{uuid.uuid4().hex[:8]}"
        )

        resp = await client.post(f"/api/v1/admin/tenants/{tenant.id}/suspend", headers=headers)
        assert resp.status_code == 409

    @pytest.mark.anyio
    async def test_cancel_irreversible(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.ACTIVE, slug=f"cancel-{uuid.uuid4().hex[:8]}"
        )

        resp = await client.post(f"/api/v1/admin/tenants/{tenant.id}/cancel", headers=headers)
        assert resp.status_code == 200
        await db_session.refresh(tenant)
        assert tenant.status == TenantStatus.CANCELLED

        # Already cancelled -> 409
        resp2 = await client.post(f"/api/v1/admin/tenants/{tenant.id}/cancel", headers=headers)
        assert resp2.status_code == 409

    @pytest.mark.anyio
    async def test_suspend_blocks_login(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.ACTIVE, slug=f"blocklogin-{uuid.uuid4().hex[:8]}"
        )
        admin = await _create_user(
            db_session,
            f"blocked-{uuid.uuid4().hex[:8]}@test.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )

        # Suspend
        await client.post(f"/api/v1/admin/tenants/{tenant.id}/suspend", headers=headers)

        # Login should fail with 403
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": _TEST_PWD},
        )
        assert login_resp.status_code == 403
        assert "suspended" in login_resp.json()["error"]["message"].lower()

    @pytest.mark.anyio
    async def test_reactivate_restores_login(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.SUSPENDED, slug=f"restore-{uuid.uuid4().hex[:8]}"
        )
        admin = await _create_user(
            db_session,
            f"restore-{uuid.uuid4().hex[:8]}@test.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )

        # Reactivate
        await client.post(f"/api/v1/admin/tenants/{tenant.id}/reactivate", headers=headers)

        # Login works
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": _TEST_PWD},
        )
        assert login_resp.status_code == 200

    @pytest.mark.anyio
    async def test_cancel_blocks_login(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(
            db_session, plan.id, TenantStatus.ACTIVE, slug=f"canclogin-{uuid.uuid4().hex[:8]}"
        )
        admin = await _create_user(
            db_session,
            f"cancelled-{uuid.uuid4().hex[:8]}@test.com",
            AdminUserRole.ADMIN,
            tenant.id,
        )

        # Cancel
        await client.post(f"/api/v1/admin/tenants/{tenant.id}/cancel", headers=headers)

        # Login 403
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": admin.email, "password": _TEST_PWD},
        )
        assert login_resp.status_code == 403
        assert "cancelled" in login_resp.json()["error"]["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# Subscription
# ═══════════════════════════════════════════════════════════════════════════


class TestSubscription:
    """GET/PATCH /api/v1/admin/tenants/{id}/subscription"""

    @pytest.mark.anyio
    async def test_get_subscription(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "GetSub")
        tenant = await _create_tenant(db_session, plan.id, slug=f"getsub-{uuid.uuid4().hex[:8]}")

        resp = await client.get(f"/api/v1/admin/tenants/{tenant.id}/subscription", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_name"] == "GetSub"
        assert "plan_id" in data
        assert "status" in data

    @pytest.mark.anyio
    async def test_update_subscription_change_plan(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan_a = await _create_plan(db_session, "PlanA")
        plan_b = await _create_plan(db_session, "PlanB")
        tenant = await _create_tenant(
            db_session, plan_a.id, slug=f"changesub-{uuid.uuid4().hex[:8]}"
        )

        resp = await client.patch(
            f"/api/v1/admin/tenants/{tenant.id}/subscription",
            json={"plan_id": str(plan_b.id)},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_name"] == "PlanB"

        # Tenant's plan_id also updated
        await db_session.refresh(tenant)
        assert tenant.plan_id == plan_b.id

    @pytest.mark.anyio
    async def test_update_subscription_status(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, slug=f"substatus-{uuid.uuid4().hex[:8]}")

        resp = await client.patch(
            f"/api/v1/admin/tenants/{tenant.id}/subscription",
            json={"status": "past_due"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "past_due"

    @pytest.mark.anyio
    async def test_update_subscription_inactive_plan_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        sa = await _create_user(
            db_session, f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan_a = await _create_plan(db_session, "ActivePlan")
        plan_b = await _create_plan(db_session, "InactivePlan")
        plan_b.is_active = False
        await db_session.flush()
        tenant = await _create_tenant(
            db_session, plan_a.id, slug=f"inactplan-{uuid.uuid4().hex[:8]}"
        )

        resp = await client.patch(
            f"/api/v1/admin/tenants/{tenant.id}/subscription",
            json={"plan_id": str(plan_b.id)},
            headers=headers,
        )
        assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════════════════════
# Audit
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditEntries:
    """Verify audit log entries created for admin actions."""

    @pytest.mark.anyio
    async def test_plan_created_audit(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(db_session, "sa-audit@zenengr.dev", AdminUserRole.SUPER_ADMIN, None)
        headers = await _auth_header(sa)

        await client.post(
            "/api/v1/admin/plans",
            json={
                "name": "AuditPlan",
                "max_admin_users": 5,
                "max_clients": 10,
                "max_active_projects": 5,
                "max_storage_mb": 256,
            },
            headers=headers,
        )

        stmt = select(AuditLog).where(AuditLog.action == "plan.created")
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_type.value == "super_admin"
        assert entry.tenant_id is None  # platform scope

    @pytest.mark.anyio
    async def test_tenant_created_audit(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(
            db_session, "sa-tenant@zenengr.dev", AdminUserRole.SUPER_ADMIN, None
        )
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "AuditTenantPlan")

        await client.post(
            "/api/v1/admin/tenants",
            json={
                "business_name": "Audit Tenant",
                "slug": f"audit-{uuid.uuid4().hex[:8]}",
                "plan_id": str(plan.id),
                "admin_email": "audit@test.com",
                "admin_full_name": "Auditor",
            },
            headers=headers,
        )

        stmt = select(AuditLog).where(AuditLog.action == "tenant.created")
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.tenant_id is None  # platform scope
        assert entry.actor_type.value == "super_admin"
        assert entry.details.get("business_name") == "Audit Tenant"

    @pytest.mark.anyio
    async def test_tenant_suspended_audit(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(db_session, "sa-susp@zenengr.dev", AdminUserRole.SUPER_ADMIN, None)
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session)
        tenant = await _create_tenant(db_session, plan.id, slug=f"suspaud-{uuid.uuid4().hex[:8]}")

        await client.post(f"/api/v1/admin/tenants/{tenant.id}/suspend", headers=headers)

        stmt = select(AuditLog).where(
            AuditLog.action == "tenant.suspended", AuditLog.entity_id == str(tenant.id)
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.tenant_id == tenant.id
        assert entry.actor_type.value == "super_admin"

    @pytest.mark.anyio
    async def test_subscription_updated_audit(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_user(db_session, "sa-sub@zenengr.dev", AdminUserRole.SUPER_ADMIN, None)
        headers = await _auth_header(sa)
        plan = await _create_plan(db_session, "SubAudit")
        tenant = await _create_tenant(db_session, plan.id, slug=f"subaud-{uuid.uuid4().hex[:8]}")

        await client.patch(
            f"/api/v1/admin/tenants/{tenant.id}/subscription",
            json={"status": "past_due"},
            headers=headers,
        )

        stmt = select(AuditLog).where(
            AuditLog.action == "subscription.updated", AuditLog.entity_id.isnot(None)
        )
        result = await db_session.execute(stmt)
        entries = result.scalars().all()
        assert len(entries) >= 1
        entry = entries[0]
        assert "before" in entry.details
        assert "after" in entry.details
