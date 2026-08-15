"""Feature flag resolution tests (catalog semantics).

Catalog keys default to True (system_default) when no override or plan
default row exists. Unknown keys resolve to False.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.models.plan import Plan
from app.models.plan_feature_default import PlanFeatureDefault
from app.models.tenant import Tenant
from app.models.tenant_feature_flag import TenantFeatureFlag
from app.services.feature_flags import (
    FEATURE_KEYS,
    get_resolved_flags,
    is_feature_enabled,
    set_override,
    set_plan_default,
)


async def _make_tenant(db_session, name: str, slug: str) -> tuple[Plan, Tenant]:
    plan = Plan(
        name=name,
        max_admin_users=1,
        max_clients=1,
        max_active_projects=1,
        max_storage_mb=1,
    )
    db_session.add(plan)
    await db_session.commit()

    t = Tenant(business_name=name, slug=slug, plan_id=plan.id)
    db_session.add(t)
    await db_session.commit()
    return plan, t


@pytest.mark.anyio
async def test_catalog_key_defaults_true_when_no_rows(db_session):
    """Catalog key with no override/plan default -> True (catalog default)."""
    _, t = await _make_tenant(db_session, "FFCatalog", "ffcatalog")

    result = await is_feature_enabled(db_session, t.id, "comments_module")
    assert result is True


@pytest.mark.anyio
async def test_unknown_key_defaults_false_when_no_rows(db_session):
    """Unknown key with no rows -> False (no catalog entry)."""
    _, t = await _make_tenant(db_session, "FFUnknown", "ffunknown")

    result = await is_feature_enabled(db_session, t.id, "nonexistent")
    assert result is False


@pytest.mark.anyio
async def test_feature_flag_plan_default(db_session):
    """Plan default True -> True when no tenant override."""
    plan, t = await _make_tenant(db_session, "FFPlanDefault", "ffplandefault")

    pfd = PlanFeatureDefault(plan_id=plan.id, key="client_portal_payments", enabled=True)
    db_session.add(pfd)
    await db_session.commit()

    result = await is_feature_enabled(db_session, t.id, "client_portal_payments")
    assert result is True


@pytest.mark.anyio
async def test_feature_flag_tenant_override_wins(db_session):
    """Tenant override overrides plan default."""
    plan, t = await _make_tenant(db_session, "FFOverride", "ffoverride")

    pfd = PlanFeatureDefault(plan_id=plan.id, key="comments_module", enabled=True)
    db_session.add(pfd)
    await db_session.commit()

    ff = TenantFeatureFlag(tenant_id=t.id, key="comments_module", enabled=False)
    db_session.add(ff)
    await db_session.commit()

    result = await is_feature_enabled(db_session, t.id, "comments_module")
    assert result is False


@pytest.mark.anyio
async def test_set_override_unknown_key_422(db_session):
    """set_override rejects keys not in the catalog with 422."""
    _, t = await _make_tenant(db_session, "FFBadOverride", "ffbadoverride")

    with pytest.raises(HTTPException) as exc:
        await set_override(db_session, t.id, "bogus_key", enabled=True)
    assert exc.value.status_code == 422
    assert exc.value.detail == "Unknown feature key: bogus_key"


@pytest.mark.anyio
async def test_set_plan_default_unknown_key_422(db_session):
    """set_plan_default rejects keys not in the catalog with 422."""
    plan, _ = await _make_tenant(db_session, "FFBadPlan", "ffbadplan")

    with pytest.raises(HTTPException) as exc:
        await set_plan_default(db_session, plan.id, "bogus_key", enabled=True)
    assert exc.value.status_code == 422
    assert exc.value.detail == "Unknown feature key: bogus_key"


@pytest.mark.anyio
async def test_set_override_known_key_ok(db_session):
    """set_override accepts catalog keys."""
    _, t = await _make_tenant(db_session, "FFOkOverride", "ffokoverride")

    flag = await set_override(db_session, t.id, "comments_module", enabled=False)
    assert flag.enabled is False
    await db_session.commit()

    assert await is_feature_enabled(db_session, t.id, "comments_module") is False


@pytest.mark.anyio
async def test_get_resolved_flags_full_catalog_with_sources(db_session):
    """No rows -> full catalog, all enabled, source system_default."""
    plan, t = await _make_tenant(db_session, "FFResolved", "ffresolved")

    resolved = await get_resolved_flags(db_session, t.id)
    assert len(resolved) == len(FEATURE_KEYS)
    by_key = {r["key"]: r for r in resolved}
    assert set(by_key) == {entry["key"] for entry in FEATURE_KEYS}
    for entry in FEATURE_KEYS:
        detail = by_key[entry["key"]]
        assert detail["enabled"] is entry["default"]
        assert detail["source"] == "system_default"


@pytest.mark.anyio
async def test_get_resolved_flags_plan_default_and_override_sources(db_session):
    """Plan default + override sources reported; unknown rows kept (back-compat)."""
    plan, t = await _make_tenant(db_session, "FFResolved2", "ffresolved2")

    db_session.add(PlanFeatureDefault(plan_id=plan.id, key="comments_module", enabled=False))
    db_session.add(TenantFeatureFlag(tenant_id=t.id, key="files_module", enabled=False))
    db_session.add(PlanFeatureDefault(plan_id=plan.id, key="legacy_flag", enabled=True))
    await db_session.commit()

    resolved = await get_resolved_flags(db_session, t.id)
    by_key = {r["key"]: r for r in resolved}

    # Catalog entries always present
    assert set(by_key) >= {entry["key"] for entry in FEATURE_KEYS}
    # Back-compat: non-catalog key with a row is still surfaced
    assert by_key["legacy_flag"]["enabled"] is True
    assert by_key["legacy_flag"]["source"] == "plan_default"
    # Override wins over plan default
    assert by_key["comments_module"]["enabled"] is False
    assert by_key["comments_module"]["source"] == "plan_default"
    assert by_key["files_module"]["enabled"] is False
    assert by_key["files_module"]["source"] == "override"


@pytest.mark.anyio
async def test_setting_defaults_defined(db_session):
    """DEFAULT_SETTINGS contains expected keys."""
    from app.services.settings import DEFAULT_SETTINGS

    keys = {s["key"] for s in DEFAULT_SETTINGS}
    assert "currency" in keys
    assert "invoice_number_format" in keys
    assert "timezone" in keys
    assert "date_format" in keys
    assert "time_format" in keys
    assert "email_sender_identity" in keys
    assert "password_min_length" in keys
    assert len(DEFAULT_SETTINGS) == 7
