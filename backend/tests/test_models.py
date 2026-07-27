"""Model round-trip and integrity tests."""

from __future__ import annotations

import uuid
from datetime import UTC

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.enums import (
    ActorType,
    AdminUserRole,
    BillingCycle,
    InviteRole,
    PermissionLevel,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.invite import Invite
from app.models.plan import Plan
from app.models.plan_feature_default import PlanFeatureDefault
from app.models.tenant import Tenant
from app.models.tenant_feature_flag import TenantFeatureFlag
from app.models.tenant_setting import TenantSetting
from app.models.tenant_subscription import TenantSubscription


@pytest.mark.anyio
async def test_plan_round_trip(db_session):
    plan = Plan(
        name="Pro Plan",
        description="For professionals",
        max_admin_users=5,
        max_clients=50,
        max_active_projects=20,
        max_storage_mb=1024,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)

    assert plan.id is not None
    assert isinstance(plan.id, uuid.UUID)
    assert plan.name == "Pro Plan"
    assert plan.description == "For professionals"
    assert plan.max_admin_users == 5
    assert plan.max_clients == 50
    assert plan.max_active_projects == 20
    assert plan.max_storage_mb == 1024
    assert plan.is_active is True
    assert plan.created_at is not None
    assert plan.updated_at is not None


@pytest.mark.anyio
async def test_plan_unique_name(db_session):
    plan1 = Plan(
        name="Unique", max_admin_users=1, max_clients=1, max_active_projects=1, max_storage_mb=1
    )
    db_session.add(plan1)
    await db_session.commit()

    plan2 = Plan(
        name="Unique", max_admin_users=1, max_clients=1, max_active_projects=1, max_storage_mb=1
    )
    db_session.add(plan2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.anyio
async def test_tenant_round_trip(db_session):
    plan = Plan(
        name="TenantPlan1",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(
        business_name="Acme Corp",
        slug="acme-corp",
        plan_id=plan.id,
        contact_info={"phone": "+1-555-0000"},
        branding={"color": "#336699"},
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    assert tenant.id is not None
    assert tenant.slug == "acme-corp"
    assert tenant.status == TenantStatus.TRIAL
    assert tenant.contact_info == {"phone": "+1-555-0000"}
    assert tenant.branding == {"color": "#336699"}
    assert tenant.logo_url is None
    assert tenant.created_at is not None


@pytest.mark.anyio
async def test_tenant_unique_slug(db_session):
    plan = Plan(
        name="SlugPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t1 = Tenant(business_name="A", slug="dupe-slug", plan_id=plan.id)
    db_session.add(t1)
    await db_session.commit()

    t2 = Tenant(business_name="B", slug="dupe-slug", plan_id=plan.id)
    db_session.add(t2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.anyio
async def test_tenant_subscription_round_trip(db_session):
    plan = Plan(
        name="SubPlan",
        max_admin_users=2,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    tenant = Tenant(business_name="Sub Tenant", slug="sub-tenant", plan_id=plan.id)
    db_session.add(tenant)
    await db_session.commit()

    sub = TenantSubscription(tenant_id=tenant.id, plan_id=plan.id, status=SubscriptionStatus.ACTIVE)
    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    assert sub.id is not None
    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.billing_cycle == BillingCycle.MONTHLY


@pytest.mark.anyio
async def test_tenant_subscription_unique_tenant(db_session):
    plan = Plan(
        name="UniqSubPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="X", slug="x-tenant", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    s1 = TenantSubscription(tenant_id=t.id, plan_id=plan.id)
    db_session.add(s1)
    await db_session.commit()

    s2 = TenantSubscription(tenant_id=t.id, plan_id=plan.id)
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.anyio
async def test_tenant_setting_unique_key_per_tenant(db_session):
    plan = Plan(
        name="SettingPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="S", slug="s-tenant", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    s1 = TenantSetting(
        tenant_id=t.id,
        key="currency",
        value="USD",
        permission_level=PermissionLevel.TENANT_ADMIN_EDITABLE,
    )
    db_session.add(s1)
    await db_session.commit()

    s2 = TenantSetting(
        tenant_id=t.id,
        key="currency",
        value="EUR",
        permission_level=PermissionLevel.TENANT_ADMIN_EDITABLE,
    )
    db_session.add(s2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.anyio
async def test_plan_feature_default_round_trip(db_session):
    plan = Plan(
        name="FFPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    pfd = PlanFeatureDefault(plan_id=plan.id, key="client_portal_payments", enabled=True)
    db_session.add(pfd)
    await db_session.commit()
    await db_session.refresh(pfd)

    assert pfd.id is not None
    assert pfd.enabled is True


@pytest.mark.anyio
async def test_tenant_feature_flag_round_trip(db_session):
    plan = Plan(
        name="FFlagPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="FF", slug="ff-tenant", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    ff = TenantFeatureFlag(tenant_id=t.id, key="comments_module", enabled=False)
    db_session.add(ff)
    await db_session.commit()
    await db_session.refresh(ff)

    assert ff.enabled is False


@pytest.mark.anyio
async def test_audit_log_append_only(db_session):
    plan = Plan(
        name="AuditPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="Audit", slug="audit-tenant", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    log = AuditLog(
        tenant_id=t.id,
        actor_id=uuid.uuid4(),
        actor_type=ActorType.SYSTEM,
        action="tenant.suspend",
        entity_type="tenant",
        entity_id=str(t.id),
        details={"reason": "payment failure"},
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    assert log.action == "tenant.suspend"
    assert log.created_at is not None
    # AuditLog should NOT have updated_at (immutable)
    assert not hasattr(log, "updated_at")


@pytest.mark.anyio
async def test_admin_user_round_trip(db_session):
    plan = Plan(
        name="AdminPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="Admin", slug="admin-tenant", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    au = AdminUser(
        tenant_id=t.id,
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashedpwd",
        role=AdminUserRole.ADMIN,
    )
    db_session.add(au)
    await db_session.commit()
    await db_session.refresh(au)

    assert au.id is not None
    assert au.role == AdminUserRole.ADMIN
    assert au.is_active is True


@pytest.mark.anyio
async def test_admin_user_unique_email(db_session):
    plan = Plan(
        name="EmailPlan",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="EmailT", slug="email-t", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    u1 = AdminUser(
        tenant_id=t.id,
        email="dupe@example.com",
        full_name="A",
        hashed_password="pwd",
        role=AdminUserRole.ADMIN,
    )
    db_session.add(u1)
    await db_session.commit()

    u2 = AdminUser(
        tenant_id=t.id,
        email="dupe@example.com",
        full_name="B",
        hashed_password="pwd",
        role=AdminUserRole.MANAGER,
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.anyio
async def test_invite_round_trip(db_session):
    plan = Plan(
        name="InvitePlan",
        max_admin_users=5,
        max_clients=10,
        max_active_projects=5,
        max_storage_mb=512,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="Invite", slug="invite-tenant", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    admin = AdminUser(
        tenant_id=t.id,
        email="inviter@example.com",
        full_name="Inviter",
        hashed_password="pwd",
        role=AdminUserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    from datetime import datetime, timedelta

    inv = Invite(
        tenant_id=t.id,
        email="invited@example.com",
        role=InviteRole.MANAGER,
        token="abc123hash",
        expires_at=datetime.now(UTC) + timedelta(days=7),
        invited_by=admin.id,
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    assert inv.id is not None
    assert inv.accepted_at is None
    assert inv.role == InviteRole.MANAGER


@pytest.mark.anyio
async def test_enum_values_persist(db_session):
    """Verify all enum values survive commit-reload cycle."""
    plan = Plan(
        name="EnumTest",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(
        business_name="EnumT",
        slug="enum-t",
        plan_id=plan.id,
        status=TenantStatus.ACTIVE,
    )
    db_session.add(t)
    await db_session.commit()

    result = await db_session.execute(select(Tenant).where(Tenant.id == t.id))
    loaded = result.scalar_one()
    assert loaded.status == TenantStatus.ACTIVE
