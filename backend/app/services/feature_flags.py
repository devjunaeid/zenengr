"""Feature flag resolution and management service.

Resolution order:
  1. TenantFeatureFlag override (tenant-specific)
  2. PlanFeatureDefault (via tenant's plan)
  3. Catalog default from FEATURE_KEYS (False for unknown keys)

FEATURE_KEYS is the feature-flag catalog (key/label/default). set_override
and set_plan_default only accept catalog keys (422 otherwise). Keys not in
the catalog remain resolvable when rows exist (back-compat) and are still
surfaced by get_resolved_flags.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan_feature_default import PlanFeatureDefault
from app.models.tenant import Tenant
from app.models.tenant_feature_flag import TenantFeatureFlag

# ── Feature-flag catalog ────────────────────────────────────────────────────

FEATURE_KEYS: list[dict[str, Any]] = [
    {"key": "projects_module", "label": "Projects", "default": True},
    {"key": "clients_module", "label": "Clients", "default": True},
    {"key": "services_module", "label": "Services", "default": True},
    {"key": "invoices_module", "label": "Invoices & Payments", "default": True},
    {"key": "files_module", "label": "Files", "default": True},
    {"key": "comments_module", "label": "Comments", "default": True},
    {"key": "notifications_module", "label": "Notifications", "default": True},
    {"key": "roles_module", "label": "Custom Roles & Permissions", "default": True},
]

FEATURE_KEY_BY_RESOURCE: dict[str, str] = {
    "projects": "projects_module",
    "milestones": "projects_module",
    "clients": "clients_module",
    "services": "services_module",
    "invoices": "invoices_module",
    "payments": "invoices_module",
    "financial_reports": "invoices_module",
    "comments": "comments_module",
    "files": "files_module",
    "roles": "roles_module",
}

_KNOWN_KEYS: frozenset[str] = frozenset(entry["key"] for entry in FEATURE_KEYS)
_CATALOG_DEFAULTS: dict[str, bool] = {entry["key"]: entry["default"] for entry in FEATURE_KEYS}


async def is_feature_enabled(session: AsyncSession, tenant_id: object, key: str) -> bool:
    """Resolve feature flag for tenant.

    Returns True if enabled via tenant override or plan default; otherwise
    falls back to the catalog default (False for unknown keys).
    """
    # 1. Check tenant-level override
    _check = await session.execute(
        select(TenantFeatureFlag).where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.key == key,
        )
    )
    flag = _check.scalar_one_or_none()
    if flag is not None:
        return flag.enabled

    # 2. Check plan-level default
    tenant = await session.get(Tenant, tenant_id)
    if tenant is not None:
        plan_default = await session.execute(
            select(PlanFeatureDefault).where(
                PlanFeatureDefault.plan_id == tenant.plan_id,
                PlanFeatureDefault.key == key,
            )
        )
        pd = plan_default.scalar_one_or_none()
        if pd is not None:
            return pd.enabled

    # 3. Catalog default (False for keys not in the catalog)
    return _CATALOG_DEFAULTS.get(key, False)


async def resolve_flag_detail(
    session: AsyncSession, tenant_id: uuid.UUID, key: str
) -> dict[str, Any]:
    """Resolve single flag with source info. Returns {key, enabled, source}."""
    # 1. Check tenant override
    _check = await session.execute(
        select(TenantFeatureFlag).where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.key == key,
        )
    )
    flag = _check.scalar_one_or_none()
    if flag is not None:
        return {"key": key, "enabled": flag.enabled, "source": "override"}

    # 2. Check plan default
    tenant = await session.get(Tenant, tenant_id)
    if tenant is not None:
        pd_check = await session.execute(
            select(PlanFeatureDefault).where(
                PlanFeatureDefault.plan_id == tenant.plan_id,
                PlanFeatureDefault.key == key,
            )
        )
        pd = pd_check.scalar_one_or_none()
        if pd is not None:
            return {"key": key, "enabled": pd.enabled, "source": "plan_default"}

    # 3. Catalog default
    return {
        "key": key,
        "enabled": _CATALOG_DEFAULTS.get(key, False),
        "source": "system_default",
    }


async def get_resolved_flags(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get all resolved flags for a tenant with source info (cached in cashews)."""
    from app.core.cache import cache, tenant_flags_cache_key

    cache_key = tenant_flags_cache_key(tenant_id)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # 1. Fetch overrides in 1 query
    override_stmt = select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id)
    override_rows = (await session.execute(override_stmt)).scalars().all()
    override_map = {o.key: o.enabled for o in override_rows}

    # 2. Fetch plan defaults in 1 query
    plan_default_map: dict[str, bool] = {}
    if tenant.plan_id is not None:
        pd_stmt = select(PlanFeatureDefault).where(PlanFeatureDefault.plan_id == tenant.plan_id)
        pd_rows = (await session.execute(pd_stmt)).scalars().all()
        plan_default_map = {pd.key: pd.enabled for pd in pd_rows}

    # 3. Resolve in memory (0 extra queries)
    known_keys: set[str] = set(_KNOWN_KEYS) | set(override_map.keys()) | set(plan_default_map.keys())

    results: list[dict[str, Any]] = []
    for key in sorted(known_keys):
        if key in override_map:
            results.append({"key": key, "enabled": override_map[key], "source": "override"})
        elif key in plan_default_map:
            results.append(
                {"key": key, "enabled": plan_default_map[key], "source": "plan_default"}
            )
        else:
            results.append(
                {
                    "key": key,
                    "enabled": _CATALOG_DEFAULTS.get(key, False),
                    "source": "system_default",
                }
            )

    await cache.set(cache_key, results, expire=300)
    return results


async def get_overrides_list(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get raw tenant feature flag overrides (no plan default resolution)."""
    result = await session.execute(
        select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id)
    )
    return [
        {"key": ff.key, "enabled": ff.enabled, "id": str(ff.id)} for ff in result.scalars().all()
    ]


def _validate_key(key: str) -> None:
    """Reject keys that are not in the feature-flag catalog (422)."""
    if key not in _KNOWN_KEYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown feature key: {key}",
        )


async def set_override(
    session: AsyncSession, tenant_id: uuid.UUID, key: str, enabled: bool
) -> TenantFeatureFlag:
    """Upsert a tenant-level feature flag override."""
    _validate_key(key)
    result = await session.execute(
        select(TenantFeatureFlag).where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.key == key,
        )
    )
    flag = result.scalar_one_or_none()
    if flag is not None:
        flag.enabled = enabled
    else:
        flag = TenantFeatureFlag(tenant_id=tenant_id, key=key, enabled=enabled)
        session.add(flag)
    await session.flush()
    await session.refresh(flag)
    from app.core.cache import invalidate_tenant_metadata

    await invalidate_tenant_metadata(tenant_id)
    return flag


async def remove_override(session: AsyncSession, tenant_id: uuid.UUID, key: str) -> None:
    """Remove a tenant-level feature flag override (fallback to plan default)."""
    result = await session.execute(
        select(TenantFeatureFlag).where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.key == key,
        )
    )
    flag = result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No override found for flag '{key}'",
        )
    await session.delete(flag)
    await session.flush()
    from app.core.cache import invalidate_tenant_metadata

    await invalidate_tenant_metadata(tenant_id)


async def get_plan_defaults(session: AsyncSession, plan_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get all plan-level feature defaults."""
    result = await session.execute(
        select(PlanFeatureDefault).where(PlanFeatureDefault.plan_id == plan_id)
    )
    return [{"key": pd.key, "enabled": pd.enabled} for pd in result.scalars().all()]


async def set_plan_default(
    session: AsyncSession, plan_id: uuid.UUID, key: str, enabled: bool
) -> PlanFeatureDefault:
    """Upsert a plan-level feature flag default."""
    _validate_key(key)
    result = await session.execute(
        select(PlanFeatureDefault).where(
            PlanFeatureDefault.plan_id == plan_id,
            PlanFeatureDefault.key == key,
        )
    )
    pd = result.scalar_one_or_none()
    if pd is not None:
        pd.enabled = enabled
    else:
        pd = PlanFeatureDefault(plan_id=plan_id, key=key, enabled=enabled)
        session.add(pd)
    await session.flush()
    await session.refresh(pd)
    from app.core.cache import cache

    await cache.clear()
    return pd
