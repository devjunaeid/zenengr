"""Feature flag resolution tests."""

from __future__ import annotations

import pytest

from app.models.plan import Plan
from app.models.plan_feature_default import PlanFeatureDefault
from app.models.tenant import Tenant
from app.models.tenant_feature_flag import TenantFeatureFlag
from app.services.feature_flags import is_feature_enabled


@pytest.mark.anyio
async def test_feature_flag_default_false(db_session):
    """No override or plan default -> False."""
    plan = Plan(
        name="FFDefault",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name="FFD", slug="ffd", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    result = await is_feature_enabled(db_session, t.id, "nonexistent")
    assert result is False


@pytest.mark.anyio
async def test_feature_flag_plan_default(db_session):
    """Plan default True -> True when no tenant override."""
    plan = Plan(
        name="FFPlanDefault",
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

    t = Tenant(business_name="FFPD", slug="ffpd", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    result = await is_feature_enabled(db_session, t.id, "client_portal_payments")
    assert result is True


@pytest.mark.anyio
async def test_feature_flag_tenant_override_wins(db_session):
    """Tenant override overrides plan default."""
    plan = Plan(
        name="FFOverride",
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    pfd = PlanFeatureDefault(plan_id=plan.id, key="comments_module", enabled=True)
    db_session.add(pfd)
    await db_session.commit()

    t = Tenant(business_name="FFO", slug="ffo", plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()

    ff = TenantFeatureFlag(tenant_id=t.id, key="comments_module", enabled=False)
    db_session.add(ff)
    await db_session.commit()

    result = await is_feature_enabled(db_session, t.id, "comments_module")
    assert result is False


@pytest.mark.anyio
async def test_setting_defaults_defined(db_session):
    """DEFAULT_SETTINGS contains expected keys."""
    from app.services.settings import DEFAULT_SETTINGS

    keys = {s["key"] for s in DEFAULT_SETTINGS}
    assert "currency" in keys
    assert "invoice_number_format" in keys
    assert "timezone" in keys
    assert "date_format" in keys
    assert "email_sender_identity" in keys
    assert len(DEFAULT_SETTINGS) == 5
