"""Feature flag resolution and management service.

Resolution order:
  1. TenantFeatureFlag override (tenant-specific)
  2. PlanFeatureDefault (via tenant's plan)
  3. False (system default)
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


async def is_feature_enabled(session: AsyncSession, tenant_id: object, key: str) -> bool:
    """Resolve feature flag for tenant.

    Returns True if enabled via tenant override or plan default.
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

    # 3. System default: disabled
    return False


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

    # 3. Default
    return {"key": key, "enabled": False, "source": "default_false"}


async def get_resolved_flags(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get all resolved flags for a tenant with source info.

    Known keys are the union of tenant overrides and plan defaults.
    """
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Collect all known keys: overrides + plan defaults
    known_keys: set[str] = set()

    overrides = await session.execute(
        select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id)
    )
    for o in overrides.scalars().all():
        known_keys.add(o.key)

    plan_defaults = await session.execute(
        select(PlanFeatureDefault).where(PlanFeatureDefault.plan_id == tenant.plan_id)
    )
    for pd in plan_defaults.scalars().all():
        known_keys.add(pd.key)

    results: list[dict[str, Any]] = []
    for key in sorted(known_keys):
        detail = await resolve_flag_detail(session, tenant_id, key)
        results.append(detail)
    return results


async def get_overrides_list(session: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    """Get raw tenant feature flag overrides (no plan default resolution)."""
    result = await session.execute(
        select(TenantFeatureFlag).where(TenantFeatureFlag.tenant_id == tenant_id)
    )
    return [
        {"key": ff.key, "enabled": ff.enabled, "id": str(ff.id)} for ff in result.scalars().all()
    ]


async def set_override(
    session: AsyncSession, tenant_id: uuid.UUID, key: str, enabled: bool
) -> TenantFeatureFlag:
    """Upsert a tenant-level feature flag override."""
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
    return pd
