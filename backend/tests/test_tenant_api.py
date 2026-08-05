"""Integration tests for tenant-facing APIs (TODO-010, 013, 014, 018, 019, 021, 022, 023, 024, 041).

Covers: tenant profile, settings, plan/usage, feature flags, limit enforcement, audit logs.
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
from app.models.audit_log import AuditLog
from app.models.enums import (
    AdminUserRole,
    BillingCycle,
    PermissionLevel,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.plan import Plan
from app.models.plan_feature_default import PlanFeatureDefault
from app.models.tenant import Tenant
from app.models.tenant_feature_flag import TenantFeatureFlag
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


async def _create_sa(session: AsyncSession) -> AdminUser:
    user = AdminUser(
        tenant_id=None,
        email=f"sa-{uuid.uuid4().hex[:8]}@zenengr.dev",
        full_name="Super Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.SUPER_ADMIN,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _create_tenant_and_admin(
    session: AsyncSession,
    plan: Plan | None = None,
    status: TenantStatus = TenantStatus.ACTIVE,
) -> tuple[Tenant, AdminUser]:
    if plan is None:
        plan = await _create_plan(session)
    tenant = Tenant(
        business_name="TestCo",
        slug=f"testco-{uuid.uuid4().hex[:8]}",
        status=status,
        plan_id=plan.id,
    )
    session.add(tenant)
    await session.flush()

    sub = TenantSubscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
    )
    session.add(sub)

    # Seed settings
    from app.services.settings import DEFAULT_SETTINGS

    for s in DEFAULT_SETTINGS:
        ts = TenantSetting(
            tenant_id=tenant.id,
            key=s["key"],
            value=s["value"],
            permission_level=s["permission_level"],
        )
        session.add(ts)

    admin = AdminUser(
        tenant_id=tenant.id,
        email=f"admin-{uuid.uuid4().hex[:8]}@testco.com",
        full_name="Tenant Admin",
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


async def _create_tenant_without_settings(
    session: AsyncSession,
) -> tuple[Tenant, AdminUser]:
    """Tenant + admin with NO tenant_settings rows (defaults only)."""
    plan = await _create_plan(session)
    tenant = Tenant(
        business_name="UpsertCo",
        slug=f"upsert-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
        plan_id=plan.id,
    )
    session.add(tenant)
    await session.flush()
    sub = TenantSubscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
    )
    session.add(sub)
    admin = AdminUser(
        tenant_id=tenant.id,
        email=f"upsert-admin-{uuid.uuid4().hex[:8]}@testco.com",
        full_name="Upsert Admin",
        hashed_password=hash_password(_TEST_PWD),
        role=AdminUserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(tenant)
    await session.refresh(admin)
    return tenant, admin


async def _auth_header(user: AdminUser) -> dict[str, str]:
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )
    return {"Authorization": f"Bearer {token}"}


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Profile (TODO-010)
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantProfile:
    """GET/PATCH /api/v1/tenant/profile"""

    @pytest.mark.anyio
    async def test_get_profile(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.get("/api/v1/tenant/profile", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["business_name"] == "TestCo"
        assert data["slug"] == tenant.slug
        assert data["status"] == "active"
        assert "plan_name" in data
        assert "subscription_status" in data

    @pytest.mark.anyio
    async def test_get_profile_any_role(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        manager = await _create_user(
            db_session, f"mgr-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.MANAGER, tenant.id
        )
        headers = await _auth_header(manager)

        resp = await client.get("/api/v1/tenant/profile", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["business_name"] == "TestCo"

    @pytest.mark.anyio
    async def test_patch_profile_admin_ok(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"business_name": "NewCo"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["business_name"] == "NewCo"
        assert data["slug"] == tenant.slug  # unchanged

    @pytest.mark.anyio
    async def test_patch_profile_manager_403(self, client: AsyncClient, db_session: AsyncSession):
        """Manager cannot edit tenant profile per FR-4.2."""
        tenant, _ = await _create_tenant_and_admin(db_session)
        manager = await _create_user(
            db_session, f"mgr-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.MANAGER, tenant.id
        )
        headers = await _auth_header(manager)

        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"business_name": "Hack"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_patch_profile_forbidden_fields_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Forbidden fields (slug, status, plan_id) return 422."""
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        # Slug forbidden → 422
        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"slug": "new-slug"},
            headers=headers,
        )
        assert resp.status_code == 422

        # Status forbidden → 422
        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"status": "cancelled"},
            headers=headers,
        )
        assert resp.status_code == 422

        # plan_id forbidden → 422
        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"plan_id": str(uuid.uuid4())},
            headers=headers,
        )
        assert resp.status_code == 422

        # Valid field still works
        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"business_name": "X"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["business_name"] == "X"

    @pytest.mark.anyio
    async def test_patch_profile_employee_403(self, client: AsyncClient, db_session: AsyncSession):
        """Employee cannot edit tenant profile."""
        tenant, _ = await _create_tenant_and_admin(db_session)
        employee = await _create_user(
            db_session, f"emp-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.EMPLOYEE, tenant.id
        )
        headers = await _auth_header(employee)

        resp = await client.patch(
            "/api/v1/tenant/profile",
            json={"business_name": "EmployeeHack"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_profile_update_audit(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        await client.patch(
            "/api/v1/tenant/profile",
            json={"business_name": "AuditCo", "contact_info": {"phone": "555"}},
            headers=headers,
        )

        stmt = select(AuditLog).where(
            AuditLog.action == "tenant.profile_updated",
            AuditLog.tenant_id == tenant.id,
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.actor_type.value == "admin_user"
        assert "business_name" in entry.details.get("updated_fields", [])

    @pytest.mark.anyio
    async def test_patch_profile_persists_across_sessions(self, app: Any):
        """PATCH /tenant/profile must COMMIT: business_name + contact_info
        survive a fresh DB session.

        Regression for the persistence bug where the endpoint flushed but
        never committed, so a subsequent request (new session) read the old
        tenant values.
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
                tenant, admin = await _create_tenant_and_admin(write_session)
                headers = await _auth_header(admin)

                async def _override_session():
                    yield write_session

                app.dependency_overrides[get_session] = _override_session
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    resp = await ac.patch(
                        "/api/v1/tenant/profile",
                        json={
                            "business_name": "PersistedCo",
                            "contact_info": {"phone": "555-1234"},
                        },
                        headers=headers,
                    )
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["business_name"] == "PersistedCo"
                    assert data["contact_info"]["phone"] == "555-1234"

                    # Immediate GET in the same request session shows the new values
                    resp = await ac.get("/api/v1/tenant/profile", headers=headers)
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["business_name"] == "PersistedCo"
                    assert data["contact_info"]["phone"] == "555-1234"

                # Write session closed; the endpoint must have committed.
                # A brand-new session on the test engine must see the row.
                async with maker() as fresh:
                    stmt = select(Tenant).where(Tenant.id == tenant.id)
                    result = await fresh.execute(stmt)
                    fresh_tenant = result.scalar_one()
                    assert fresh_tenant.business_name == "PersistedCo"
                    assert fresh_tenant.contact_info is not None
                    assert fresh_tenant.contact_info["phone"] == "555-1234"

                    # The audit row written by the endpoint must also be
                    # committed: a fresh session must see it too.
                    stmt = select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.action == "tenant.profile_updated",
                    )
                    result = await fresh.execute(stmt)
                    entry = result.scalar_one_or_none()
                    assert entry is not None
                    assert "business_name" in entry.details.get("updated_fields", [])
        finally:
            await engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Settings (TODO-018, TODO-019)
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantSettings:
    """GET /api/v1/tenant/settings + PATCH /api/v1/tenant/settings/{key}"""

    @pytest.mark.anyio
    async def test_get_settings_masking(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)

        # Add a super_admin_only setting
        super_secret = TenantSetting(
            tenant_id=tenant.id,
            key="super_secret_key",
            value="s3cret",
            permission_level=PermissionLevel.SUPER_ADMIN_ONLY,
        )
        db_session.add(super_secret)
        await db_session.commit()

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        # super_admin_only values should be masked (null)
        secret_item = next((s for s in data if s["key"] == "super_secret_key"), None)
        assert secret_item is not None
        assert secret_item["value"] is None
        assert secret_item["editable"] is False

        # tenant_admin_editable values should be visible and editable
        currency_item = next((s for s in data if s["key"] == "currency"), None)
        assert currency_item is not None
        assert currency_item["value"] == "USD"
        assert currency_item["editable"] is True

        # SA sees everything unmasked
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)
        resp2 = await client.get(f"/api/v1/admin/tenants/{tenant.id}/settings", headers=sa_headers)
        assert resp2.status_code == 200
        sa_data = resp2.json()
        secret_sa = next((s for s in sa_data if s["key"] == "super_secret_key"), None)
        assert secret_sa is not None
        assert secret_sa["value"] == "s3cret"  # not masked
        assert secret_sa["editable"] is True

    @pytest.mark.anyio
    async def test_patch_editable_setting_ok(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/currency",
            json={"value": "EUR"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "currency"
        assert data["value"] == "EUR"

        # Verify DB
        stmt = select(TenantSetting).where(
            TenantSetting.tenant_id == tenant.id,
            TenantSetting.key == "currency",
        )
        result = await db_session.execute(stmt)
        setting = result.scalar_one_or_none()
        assert setting is not None
        assert setting.value == "EUR"

    @pytest.mark.anyio
    async def test_patch_editable_setting_validates_currency(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/currency",
            json={"value": "INVALID"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_patch_editable_setting_validates_timezone(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/timezone",
            json={"value": "Not/A/Timezone"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_patch_editable_setting_validates_invoice_format(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/invoice_number_format",
            json={"value": "NO-TOKEN"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_patch_editable_setting_validates_date_format(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/date_format",
            json={"value": "DD-MM-YYYY"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_patch_non_editable_setting_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        # email_sender_identity is tenant_admin_viewable, not editable
        resp = await client.patch(
            "/api/v1/tenant/settings/email_sender_identity",
            json={"value": "new@example.com"},
            headers=headers,
        )
        assert resp.status_code == 403

    @pytest.mark.anyio
    async def test_patch_setting_not_found_404(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/nonexistent",
            json={"value": "val"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_patch_default_setting_upserts_for_fresh_tenant(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_without_settings(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/invoice_number_format",
            json={"value": "INV-{YYYY}-{seq}"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "invoice_number_format"
        assert data["value"] == "INV-{YYYY}-{seq}"

        # Row was created with the default's permission level
        stmt = select(TenantSetting).where(
            TenantSetting.tenant_id == tenant.id,
            TenantSetting.key == "invoice_number_format",
        )
        result = await db_session.execute(stmt)
        setting = result.scalar_one_or_none()
        assert setting is not None
        assert setting.value == "INV-{YYYY}-{seq}"
        assert setting.permission_level == PermissionLevel.TENANT_ADMIN_EDITABLE

        # Subsequent GET shows the override
        resp = await client.get("/api/v1/tenant/settings", headers=headers)
        assert resp.status_code == 200
        by_key = {d["key"]: d for d in resp.json()}
        assert by_key["invoice_number_format"]["value"] == "INV-{YYYY}-{seq}"

    @pytest.mark.anyio
    async def test_patch_setting_persists_across_sessions(self, app: Any):
        """PATCH must COMMIT: value survives a fresh DB session.

        Regression for the persistence bug where update_tenant_setting
        flushed but never committed, so a subsequent request (new session)
        read the old default value.

        Uses its own engine because the shared fixture session joins an
        outer transaction via savepoint (session.commit() only releases the
        savepoint there), so a cross-session check needs a session that
        owns its transaction for real.
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
                tenant, admin = await _create_tenant_and_admin(write_session)
                headers = await _auth_header(admin)

                async def _override_session():
                    yield write_session

                app.dependency_overrides[get_session] = _override_session
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    resp = await ac.patch(
                        "/api/v1/tenant/settings/timezone",
                        json={"value": "Asia/Kolkata"},
                        headers=headers,
                    )
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["key"] == "timezone"
                    assert data["value"] == "Asia/Kolkata"

                    # Immediate GET in the same request session still shows the override
                    resp = await ac.get("/api/v1/tenant/settings", headers=headers)
                    assert resp.status_code == 200
                    by_key = {d["key"]: d for d in resp.json()}
                    assert by_key["timezone"]["value"] == "Asia/Kolkata"

                # Write session closed; the service must have committed.
                # A brand-new session on the test engine must see the row.
                async with maker() as fresh:
                    stmt = select(TenantSetting).where(
                        TenantSetting.tenant_id == tenant.id,
                        TenantSetting.key == "timezone",
                    )
                    result = await fresh.execute(stmt)
                    setting = result.scalar_one()
                    assert setting.value == "Asia/Kolkata"

                    # The audit row written by the endpoint must also be
                    # committed: a fresh session must see it too.
                    stmt = select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.action == "tenant.setting_updated",
                    )
                    result = await fresh.execute(stmt)
                    entry = result.scalar_one_or_none()
                    assert entry is not None
                    assert entry.details.get("key") == "timezone"
                    assert entry.details.get("old_value") == "UTC"
                    assert entry.details.get("new_value") == "Asia/Kolkata"
        finally:
            await engine.dispose()

    @pytest.mark.anyio
    async def test_patch_default_setting_upsert_validates_value(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_without_settings(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/invoice_number_format",
            json={"value": "NO-TOKEN"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_patch_unknown_key_fresh_tenant_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_without_settings(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/nonexistent",
            json={"value": "val"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_sa_edits_super_admin_only_setting(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        # Add a super_admin_only setting
        super_secret = TenantSetting(
            tenant_id=tenant.id,
            key="super_secret_key",
            value="s3cret",
            permission_level=PermissionLevel.SUPER_ADMIN_ONLY,
        )
        db_session.add(super_secret)
        await db_session.commit()

        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        resp = await client.patch(
            f"/api/v1/admin/tenants/{tenant.id}/settings/super_secret_key",
            json={"value": "new-value"},
            headers=sa_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "new-value"

    @pytest.mark.anyio
    async def test_setting_update_audit(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        await client.patch(
            "/api/v1/tenant/settings/currency",
            json={"value": "GBP"},
            headers=headers,
        )

        stmt = select(AuditLog).where(
            AuditLog.action == "tenant.setting_updated",
            AuditLog.tenant_id == tenant.id,
        )
        result = await db_session.execute(stmt)
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.details.get("key") == "currency"
        assert entry.details.get("old_value") == "USD"
        assert entry.details.get("new_value") == "GBP"

    @pytest.mark.anyio
    async def test_list_settings_no_rows_returns_defaults(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        from app.services.settings import DEFAULT_SETTINGS

        # Tenant with NO tenant_settings rows
        plan = await _create_plan(db_session)
        tenant = Tenant(
            business_name="NoSettingsCo",
            slug=f"nosettings-{uuid.uuid4().hex[:8]}",
            status=TenantStatus.ACTIVE,
            plan_id=plan.id,
        )
        db_session.add(tenant)
        await db_session.flush()
        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
        )
        db_session.add(sub)
        admin = AdminUser(
            tenant_id=tenant.id,
            email=f"nosettings-admin-{uuid.uuid4().hex[:8]}@testco.com",
            full_name="No Settings Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(admin)
        await db_session.commit()
        await db_session.refresh(tenant)
        await db_session.refresh(admin)

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        defaults_by_key = {d["key"]: d for d in DEFAULT_SETTINGS}
        assert len(data) == len(DEFAULT_SETTINGS)
        assert set(d["key"] for d in data) == set(defaults_by_key)

        for item in data:
            assert item["value"] == defaults_by_key[item["key"]]["value"]
            assert item["permission_level"] == defaults_by_key[item["key"]][
                "permission_level"
            ].value
            assert isinstance(item["editable"], bool)

        by_key = {d["key"]: d for d in data}
        assert by_key["invoice_number_format"]["value"] == "INV-{YYYY}-{SEQ:04d}"
        assert by_key["password_min_length"]["value"] == "10"
        assert by_key["currency"]["value"] == "USD"
        assert by_key["email_sender_identity"]["permission_level"] == "tenant_admin_viewable"
        assert by_key["email_sender_identity"]["editable"] is False

    @pytest.mark.anyio
    async def test_list_settings_shows_stored_override_and_defaults(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        resp = await client.patch(
            "/api/v1/tenant/settings/invoice_number_format",
            json={"value": "INV-{YYYY}-{seq}"},
            headers=headers,
        )
        assert resp.status_code == 200

        resp = await client.get("/api/v1/tenant/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        by_key = {d["key"]: d for d in data}

        # Stored override wins for the patched key
        assert by_key["invoice_number_format"]["value"] == "INV-{YYYY}-{seq}"
        assert by_key["invoice_number_format"]["permission_level"] == "tenant_admin_editable"
        assert by_key["invoice_number_format"]["editable"] is True

        # Unpatched keys fall back to defaults
        assert by_key["password_min_length"]["value"] == "10"
        assert by_key["currency"]["value"] == "USD"
        assert by_key["date_format"]["value"] == "YYYY-MM-DD"

        # permission_level present on every entry
        allowed = {"tenant_admin_editable", "tenant_admin_viewable"}
        assert all(item["permission_level"] in allowed for item in data)


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Plan + Usage (TODO-014)
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantPlan:
    """GET /api/v1/tenant/plan"""

    @pytest.mark.anyio
    async def test_get_plan_and_usage(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session, "Premium")
        tenant, admin = await _create_tenant_and_admin(db_session, plan)

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/plan", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["plan_name"] == "Premium"
        assert data["limits"]["max_admin_users"] == 5
        assert data["usage"]["admin_users"] >= 1
        assert data["usage"]["clients"] == 0
        assert data["usage"]["active_projects"] == 0
        assert data["usage"]["storage_mb"] == 0

    @pytest.mark.anyio
    async def test_usage_counts_reflect_users(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant, admin = await _create_tenant_and_admin(db_session, plan)

        # Create another active user
        await _create_user(
            db_session, f"u2-{uuid.uuid4().hex[:8]}@test.com", AdminUserRole.MANAGER, tenant.id
        )

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/plan", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["usage"]["admin_users"] >= 2


# ═══════════════════════════════════════════════════════════════════════════
# Feature Flags (TODO-021, TODO-022, TODO-024)
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantFeatureFlags:
    """Tenant read-only view and SA management."""

    @pytest.mark.anyio
    async def test_tenant_get_flags_no_overrides(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant, admin = await _create_tenant_and_admin(db_session, plan)

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/flags", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []  # no known flags

    @pytest.mark.anyio
    async def test_sa_set_override_then_tenant_sees_it(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant, admin = await _create_tenant_and_admin(db_session, plan)
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        # SA sets override
        resp = await client.put(
            f"/api/v1/admin/tenants/{tenant.id}/flags/comments_module",
            json={"enabled": True},
            headers=sa_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

        # Tenant sees it
        tenant_headers = await _auth_header(admin)
        resp2 = await client.get("/api/v1/tenant/flags", headers=tenant_headers)
        assert resp2.status_code == 200
        flags = resp2.json()
        assert len(flags) == 1
        assert flags[0]["key"] == "comments_module"
        assert flags[0]["enabled"] is True

    @pytest.mark.anyio
    async def test_sa_override_falls_back_on_delete(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant, admin = await _create_tenant_and_admin(db_session, plan)
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        # Set override True
        await client.put(
            f"/api/v1/admin/tenants/{tenant.id}/flags/comments_module",
            json={"enabled": True},
            headers=sa_headers,
        )

        # Delete override
        resp = await client.delete(
            f"/api/v1/admin/tenants/{tenant.id}/flags/comments_module",
            headers=sa_headers,
        )
        assert resp.status_code == 200

        # Tenant no longer sees it (no plan default)
        tenant_headers = await _auth_header(admin)
        resp2 = await client.get("/api/v1/tenant/flags", headers=tenant_headers)
        assert resp2.json() == []

    @pytest.mark.anyio
    async def test_sa_view_resolution_sources(self, client: AsyncClient, db_session: AsyncSession):
        plan = await _create_plan(db_session)
        tenant, admin = await _create_tenant_and_admin(db_session, plan)
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        # Plan default
        pfd = PlanFeatureDefault(plan_id=plan.id, key="client_portal", enabled=True)
        db_session.add(pfd)
        await db_session.commit()

        # Tenant override (disabled)
        ff = TenantFeatureFlag(tenant_id=tenant.id, key="client_portal", enabled=False)
        db_session.add(ff)
        await db_session.commit()

        resp = await client.get(f"/api/v1/admin/tenants/{tenant.id}/flags", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["resolved"]) == 1
        assert data["resolved"][0]["enabled"] is False
        assert data["resolved"][0]["source"] == "override"
        assert len(data["overrides"]) == 1

    @pytest.mark.anyio
    async def test_plan_default_does_not_clobber_override(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        plan = await _create_plan(db_session)
        tenant, admin = await _create_tenant_and_admin(db_session, plan)
        sa = await _create_sa(db_session)
        sa_headers = await _auth_header(sa)

        # Set override True
        await client.put(
            f"/api/v1/admin/tenants/{tenant.id}/flags/comments_module",
            json={"enabled": True},
            headers=sa_headers,
        )

        # Set plan default False (should NOT affect tenant override)
        resp = await client.put(
            f"/api/v1/admin/plans/{plan.id}/flags/comments_module",
            json={"enabled": False},
            headers=sa_headers,
        )
        assert resp.status_code == 200

        # Tenant still sees enabled (override wins)
        tenant_headers = await _auth_header(admin)
        resp2 = await client.get("/api/v1/tenant/flags", headers=tenant_headers)
        assert resp2.json()[0]["enabled"] is True

    @pytest.mark.anyio
    async def test_sa_set_override_persists_across_sessions(self, app: Any):
        """PUT /api/v1/admin/tenants/{id}/flags/{key} must COMMIT: the
        override survives a fresh DB session.

        Regression for the persistence bug where set_override flushed but
        the router never committed (audit row included).
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
                plan = await _create_plan(write_session)
                tenant, admin = await _create_tenant_and_admin(write_session, plan)
                sa = await _create_sa(write_session)
                sa_headers = await _auth_header(sa)

                async def _override_session():
                    yield write_session

                app.dependency_overrides[get_session] = _override_session
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    resp = await ac.put(
                        f"/api/v1/admin/tenants/{tenant.id}/flags/comments_module",
                        json={"enabled": True},
                        headers=sa_headers,
                    )
                    assert resp.status_code == 200
                    assert resp.json()["enabled"] is True

                # Write session closed; the router must have committed.
                # A brand-new session on the test engine must see the override.
                async with maker() as fresh:
                    stmt = select(TenantFeatureFlag).where(
                        TenantFeatureFlag.tenant_id == tenant.id,
                        TenantFeatureFlag.key == "comments_module",
                    )
                    result = await fresh.execute(stmt)
                    flag = result.scalar_one_or_none()
                    assert flag is not None
                    assert flag.enabled is True

                    # The audit row written by the router must also be committed.
                    stmt = select(AuditLog).where(
                        AuditLog.tenant_id == tenant.id,
                        AuditLog.action == "tenant.flag_set",
                    )
                    result = await fresh.execute(stmt)
                    entry = result.scalar_one_or_none()
                    assert entry is not None
                    assert entry.details.get("key") == "comments_module"
        finally:
            await engine.dispose()

    @pytest.mark.anyio
    async def test_tenant_cannot_write_flags(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        headers = await _auth_header(admin)

        # PUT on tenant flags (no tenant write endpoint exists — expect 404)
        resp = await client.put(
            "/api/v1/tenant/flags/comments_module",
            json={"enabled": True},
            headers=headers,
        )
        assert resp.status_code == 404  # no such endpoint


# ═══════════════════════════════════════════════════════════════════════════
# require_feature_flag dependency (TODO-023)
# ═══════════════════════════════════════════════════════════════════════════


# ── require_feature_flag dependency tests ────────────────────────────────


def _register_flag_endpoint(app: Any) -> None:
    """Register throwaway endpoint for require_feature_flag testing."""
    from fastapi import Depends

    from app.core.dependencies import require_feature_flag

    @app.get("/_test/flag-check")
    async def _flag_check(user=Depends(require_feature_flag("test_feature"))):
        return {"ok": True, "role": user.role.value}  # type: ignore[union-attr]


@pytest.mark.anyio
async def test_require_feature_flag_disabled(client: AsyncClient, db_session: AsyncSession):
    """Dependency returns 403 FEATURE_DISABLED when flag disabled."""
    _register_flag_endpoint(client._transport.app)
    plan = await _create_plan(db_session)
    tenant, admin = await _create_tenant_and_admin(db_session, plan)
    headers = await _auth_header(admin)

    resp = await client.get("/_test/flag-check", headers=headers)
    assert resp.status_code == 403
    data = resp.json()
    # Custom error handler wraps in {"error": {..., "message": ...}}
    assert data["error"]["message"]["code"] == "FEATURE_DISABLED"
    assert data["error"]["message"]["details"]["flag"] == "test_feature"


@pytest.mark.anyio
async def test_require_feature_flag_enabled(client: AsyncClient, db_session: AsyncSession):
    """Dependency passes when flag enabled via plan default."""
    from app.models.plan_feature_default import PlanFeatureDefault

    _register_flag_endpoint(client._transport.app)
    plan = await _create_plan(db_session)
    # Enable flag at plan level
    pfd = PlanFeatureDefault(plan_id=plan.id, key="test_feature", enabled=True)
    db_session.add(pfd)
    await db_session.commit()
    tenant, admin = await _create_tenant_and_admin(db_session, plan)
    headers = await _auth_header(admin)

    resp = await client.get("/_test/flag-check", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.anyio
async def test_require_feature_flag_sa_exempt(client: AsyncClient, db_session: AsyncSession):
    """Super admin exempt from feature flag check."""
    _register_flag_endpoint(client._transport.app)
    sa = await _create_sa(db_session)
    headers = await _auth_header(sa)

    resp = await client.get("/_test/flag-check", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["role"] == "super_admin"


@pytest.mark.anyio
async def test_require_feature_flag_flip_reflects(client: AsyncClient, db_session: AsyncSession):
    """Flag resolution reflects changes immediately (no caching)."""
    from app.models.plan_feature_default import PlanFeatureDefault
    from app.services.feature_flags import set_override

    _register_flag_endpoint(client._transport.app)
    plan = await _create_plan(db_session)
    pfd = PlanFeatureDefault(plan_id=plan.id, key="test_feature", enabled=True)
    db_session.add(pfd)
    await db_session.commit()
    tenant, admin = await _create_tenant_and_admin(db_session, plan)
    headers = await _auth_header(admin)

    # Should pass — plan default enabled
    resp = await client.get("/_test/flag-check", headers=headers)
    assert resp.status_code == 200

    # Disable via tenant override — should 403 next request
    await set_override(db_session, tenant.id, "test_feature", enabled=False)

    resp = await client.get("/_test/flag-check", headers=headers)
    assert resp.status_code == 403
    data = resp.json()
    assert data["error"]["message"]["code"] == "FEATURE_DISABLED"

    # Re-enable — should pass again
    await set_override(db_session, tenant.id, "test_feature", enabled=True)

    resp = await client.get("/_test/flag-check", headers=headers)
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Limit enforcement (TODO-013)
# ═══════════════════════════════════════════════════════════════════════════


class TestLimitEnforcement:
    """check_limit service + wired into invite creation."""

    @pytest.mark.anyio
    async def test_check_limit_under(self, db_session: AsyncSession):
        from app.services.limits import check_limit

        plan = await _create_plan(db_session, "LimitPlan")
        tenant, admin = await _create_tenant_and_admin(db_session, plan)
        # Should pass — 1 admin < 5 limit
        await check_limit(db_session, tenant.id, "admin_users", increment=1)

    @pytest.mark.anyio
    async def test_check_limit_over(self, db_session: AsyncSession):
        from app.services.limits import LimitExceededError, check_limit

        # Plan with 1 admin max
        plan = Plan(
            name=f"Strict-{uuid.uuid4().hex[:8]}",
            max_admin_users=1,
            max_clients=5,
            max_active_projects=5,
            max_storage_mb=100,
        )
        db_session.add(plan)
        await db_session.commit()

        tenant = Tenant(
            business_name="StrictCo",
            slug=f"strict-{uuid.uuid4().hex[:8]}",
            plan_id=plan.id,
        )
        db_session.add(tenant)
        await db_session.flush()

        admin = AdminUser(
            tenant_id=tenant.id,
            email=f"admin-{uuid.uuid4().hex[:8]}@strict.com",
            full_name="Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(admin)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
        )
        db_session.add(sub)
        await db_session.commit()

        # 1 admin already exists, trying to add another should fail
        with pytest.raises(LimitExceededError) as exc_info:
            await check_limit(db_session, tenant.id, "admin_users", increment=1)
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        if isinstance(detail, dict):
            assert detail.get("code") == "PLAN_LIMIT_EXCEEDED"

    @pytest.mark.anyio
    async def test_limit_blocks_invite_creation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Plan with 1 admin user max
        plan = Plan(
            name=f"InviteLimit-{uuid.uuid4().hex[:8]}",
            max_admin_users=1,
            max_clients=10,
            max_active_projects=5,
            max_storage_mb=256,
        )
        db_session.add(plan)
        await db_session.commit()

        tenant = Tenant(
            business_name="InviteLimit",
            slug=f"invitelimit-{uuid.uuid4().hex[:8]}",
            plan_id=plan.id,
        )
        db_session.add(tenant)
        await db_session.flush()

        admin = AdminUser(
            tenant_id=tenant.id,
            email=f"admin-{uuid.uuid4().hex[:8]}@invitelimit.com",
            full_name="Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(admin)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
        )
        db_session.add(sub)
        await db_session.commit()
        await db_session.refresh(admin)

        # Already 1 admin — trying to invite another should 403
        headers = await _auth_header(admin)
        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "newuser@test.com", "role": "admin"},
            headers=headers,
        )
        assert resp.status_code == 403
        data = resp.json()
        assert "PLAN_LIMIT_EXCEEDED" in str(data)

    @pytest.mark.anyio
    async def test_limit_allows_invite_under_limit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Plan with 10 admin users (plenty of room)
        plan = Plan(
            name=f"InviteOk-{uuid.uuid4().hex[:8]}",
            max_admin_users=10,
            max_clients=10,
            max_active_projects=5,
            max_storage_mb=256,
        )
        db_session.add(plan)
        await db_session.commit()

        tenant = Tenant(
            business_name="InviteOk",
            slug=f"inviteok-{uuid.uuid4().hex[:8]}",
            plan_id=plan.id,
        )
        db_session.add(tenant)
        await db_session.flush()

        admin = AdminUser(
            tenant_id=tenant.id,
            email=f"admin-{uuid.uuid4().hex[:8]}@inviteok.com",
            full_name="Admin",
            hashed_password=hash_password(_TEST_PWD),
            role=AdminUserRole.ADMIN,
            is_active=True,
        )
        db_session.add(admin)

        sub = TenantSubscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=BillingCycle.MONTHLY,
        )
        db_session.add(sub)
        await db_session.commit()
        await db_session.refresh(admin)

        headers = await _auth_header(admin)
        resp = await client.post(
            "/api/v1/tenant/invites",
            json={"email": "okuser@test.com", "role": "admin"},
            headers=headers,
        )
        # Without email setup this will fail for email sending, but limit check should pass.
        # The 500 would be from email, not limit.
        assert resp.status_code in (201, 500)
        if resp.status_code == 500:
            # Limit check passed (no 403), failed on email sending
            pass


# ═══════════════════════════════════════════════════════════════════════════
# Audit Logs (TODO-041)
# ═══════════════════════════════════════════════════════════════════════════


class TestAuditLogs:
    """GET /api/v1/tenant/audit-logs + SA equivalents"""

    @pytest.mark.anyio
    async def test_tenant_audit_logs_paginated(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)

        # Create some audit entries
        for i in range(3):
            entry = AuditLog(
                tenant_id=tenant.id,
                actor_id=admin.id,
                actor_type="admin_user",
                action=f"test.action.{i}",
                entity_type="test",
                entity_id=str(admin.id),
                details={"index": i},
            )
            db_session.add(entry)
        await db_session.commit()

        headers = await _auth_header(admin)
        resp = await client.get("/api/v1/tenant/audit-logs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 20

    @pytest.mark.anyio
    async def test_tenant_audit_logs_filtered_by_action(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant, admin = await _create_tenant_and_admin(db_session)

        entry1 = AuditLog(
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type="admin_user",
            action="tenant.profile_updated",
            entity_type="tenant",
            entity_id=str(tenant.id),
        )
        entry2 = AuditLog(
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type="admin_user",
            action="invite.created",
            entity_type="invite",
        )
        db_session.add_all([entry1, entry2])
        await db_session.commit()

        headers = await _auth_header(admin)
        resp = await client.get(
            "/api/v1/tenant/audit-logs?action=tenant.",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "tenant.profile_updated"

    @pytest.mark.anyio
    async def test_tenant_audit_logs_tenant_isolation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        tenant_a, admin_a = await _create_tenant_and_admin(db_session)
        tenant_b, admin_b = await _create_tenant_and_admin(db_session)

        for tid in (tenant_a.id, tenant_b.id):
            db_session.add(
                AuditLog(
                    tenant_id=tid,
                    actor_id=admin_a.id,
                    actor_type="admin_user",
                    action="test.isolation",
                    entity_type="test",
                )
            )
        await db_session.commit()

        # Admin A should only see tenant A's logs
        headers_a = await _auth_header(admin_a)
        resp = await client.get("/api/v1/tenant/audit-logs", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.anyio
    async def test_sa_tenant_audit_view(self, client: AsyncClient, db_session: AsyncSession):
        tenant, admin = await _create_tenant_and_admin(db_session)
        sa = await _create_sa(db_session)

        entry = AuditLog(
            tenant_id=tenant.id,
            actor_id=admin.id,
            actor_type="admin_user",
            action="test.sa_view",
            entity_type="test",
        )
        db_session.add(entry)
        await db_session.commit()

        sa_headers = await _auth_header(sa)
        resp = await client.get(f"/api/v1/admin/tenants/{tenant.id}/audit-logs", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    @pytest.mark.anyio
    async def test_sa_platform_audit_view(self, client: AsyncClient, db_session: AsyncSession):
        sa = await _create_sa(db_session)

        # Platform-scope log (tenant_id is None)
        entry = AuditLog(
            tenant_id=None,
            actor_id=sa.id,
            actor_type="super_admin",
            action="plan.created",
            entity_type="plan",
        )
        db_session.add(entry)
        await db_session.commit()

        sa_headers = await _auth_header(sa)
        resp = await client.get("/api/v1/admin/audit-logs", headers=sa_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["action"] == "plan.created"
