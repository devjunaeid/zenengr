"""Tenant-facing self-service APIs.

All endpoints scoped to the caller's own tenant.
Base path: /api/v1/tenant
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.enums import ActorType
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.schemas.tenant import (
    AuditLogEntry,
    AuditLogPage,
    FeatureFlagItem,
    PlanLimits,
    TenantPlanResponse,
    TenantProfileResponse,
    TenantProfileUpdateRequest,
    TenantSettingItem,
    TenantSettingUpdateRequest,
    UsageCounts,
)
from app.services.audit import log as audit_log
from app.services.feature_flags import get_resolved_flags
from app.services.settings import (
    can_edit_setting,
    get_tenant_settings,
    should_mask_value,
    update_tenant_setting,
)

router = APIRouter(prefix="/tenant", tags=["tenant"])


def _get_tenant_or_raise(user: AdminUser) -> uuid.UUID:
    """Get current user's tenant_id or raise 403."""
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Profile
# ═══════════════════════════════════════════════════════════════════════════


async def _load_tenant_with_relations(
    session: AsyncSession, tenant_id: uuid.UUID
) -> Tenant | None:
    """Load tenant with subscription and plan eager-loaded."""
    stmt = (
        select(Tenant)
        .options(selectinload(Tenant.subscription), selectinload(Tenant.plan))
        .where(Tenant.id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


@router.get("/profile", response_model=TenantProfileResponse)
async def get_tenant_profile(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> TenantProfileResponse:
    """Get current tenant profile."""
    tenant_id = _get_tenant_or_raise(user)
    tenant = await _load_tenant_with_relations(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    plan_name = tenant.plan.name if tenant.plan else "Unknown"
    sub_status = tenant.subscription.status if tenant.subscription else None

    return TenantProfileResponse(
        id=tenant.id,
        business_name=tenant.business_name,
        slug=tenant.slug,
        status=tenant.status,
        contact_info=tenant.contact_info,
        branding=tenant.branding,
        logo_url=tenant.logo_url,
        plan_name=plan_name,
        plan_id=tenant.plan_id,
        subscription_status=sub_status,
    )


@router.patch("/profile", response_model=TenantProfileResponse)
async def update_tenant_profile(
    body: TenantProfileUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "profile")),
) -> TenantProfileResponse:
    """Update tenant profile fields. Admin only.

    Slug, status, plan, and flags cannot be changed here.
    """
    tenant_id = _get_tenant_or_raise(user)
    tenant = await _load_tenant_with_relations(session, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Build update kwargs
    update_kwargs: dict[str, Any] = {}
    if body.business_name is not None:
        update_kwargs["business_name"] = body.business_name
    if body.contact_info is not None:
        update_kwargs["contact_info"] = body.contact_info
    if body.branding is not None:
        update_kwargs["branding"] = body.branding

    if update_kwargs:
        for key, val in update_kwargs.items():
            setattr(tenant, key, val)
        await session.flush()
        await session.refresh(tenant)

        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=user.id,
            actor_type=ActorType.ADMIN_USER,
            action="tenant.profile_updated",
            entity_type="tenant",
            entity_id=str(tenant.id),
            details={"updated_fields": list(update_kwargs.keys())},
        )

    # Return fresh profile
    plan_name = tenant.plan.name if tenant.plan else "Unknown"
    sub_status = tenant.subscription.status if tenant.subscription else None

    return TenantProfileResponse(
        id=tenant.id,
        business_name=tenant.business_name,
        slug=tenant.slug,
        status=tenant.status,
        contact_info=tenant.contact_info,
        branding=tenant.branding,
        logo_url=tenant.logo_url,
        plan_name=plan_name,
        plan_id=tenant.plan_id,
        subscription_status=sub_status,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Settings
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/settings", response_model=list[TenantSettingItem])
async def list_tenant_settings(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[TenantSettingItem]:
    """Get all settings for current tenant with editable flags and masking."""
    tenant_id = _get_tenant_or_raise(user)
    items = await get_tenant_settings(session, tenant_id, user.role)
    return [TenantSettingItem(**item) for item in items]


@router.patch("/settings/{key}", response_model=TenantSettingItem)
async def update_tenant_setting_endpoint(
    key: str,
    body: TenantSettingUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "tenant_settings")),
) -> TenantSettingItem:
    """Update a tenant setting. Admin only, key must be tenant_admin_editable."""
    tenant_id = _get_tenant_or_raise(user)

    # Fetch setting to check permission level
    from app.services.settings import get_tenant_setting_by_key

    setting = await get_tenant_setting_by_key(session, tenant_id, key)
    if setting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found",
        )

    if not can_edit_setting(setting.permission_level, user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Setting '{key}' is not editable by your role",
        )

    # Update
    result = await update_tenant_setting(session, tenant_id, key, body.value)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=user.id,
        actor_type=ActorType.ADMIN_USER,
        action="tenant.setting_updated",
        entity_type="tenant_setting",
        entity_id=key,
        details={"key": key, "old_value": result["old_value"], "new_value": result["new_value"]},
    )

    updated = await get_tenant_setting_by_key(session, tenant_id, key)
    value: str | None = updated.value if updated else None
    if updated and should_mask_value(updated.permission_level, user.role):
        value = None

    return TenantSettingItem(
        key=key,
        value=value,
        permission_level=updated.permission_level.value if updated else "",
        editable=can_edit_setting(updated.permission_level, user.role) if updated else False,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Plan + Usage
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/plan", response_model=TenantPlanResponse)
async def get_tenant_plan_and_usage(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> TenantPlanResponse:
    """Get current plan limits and usage counts for tenant."""
    tenant_id = _get_tenant_or_raise(user)
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    plan = await session.get(Plan, tenant.plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    # Count admin_users (active only)
    admin_count_stmt = select(func.count()).where(
        AdminUser.tenant_id == tenant_id,
        AdminUser.is_active == True,  # noqa: E712
    )
    admin_count_result = await session.execute(admin_count_stmt)
    admin_count: int = admin_count_result.scalar_one()

    return TenantPlanResponse(
        plan_name=plan.name,
        limits=PlanLimits(
            max_admin_users=plan.max_admin_users,
            max_clients=plan.max_clients,
            max_active_projects=plan.max_active_projects,
            max_storage_mb=plan.max_storage_mb,
        ),
        usage=UsageCounts(
            admin_users=admin_count,
            clients=0,  # TODO: wire to Client model
            active_projects=0,  # TODO: wire to Project model
            storage_mb=0,  # TODO: wire to storage tracking
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Feature Flags (read-only for tenant)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/flags", response_model=list[FeatureFlagItem])
async def list_tenant_flags(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[FeatureFlagItem]:
    """Get resolved feature flags for current tenant. Read-only."""
    tenant_id = _get_tenant_or_raise(user)
    resolved = await get_resolved_flags(session, tenant_id)
    return [FeatureFlagItem(key=r["key"], enabled=r["enabled"]) for r in resolved]


# ═══════════════════════════════════════════════════════════════════════════
# Audit Logs (Admin only)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/audit-logs", response_model=AuditLogPage)
async def list_tenant_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, min_length=1),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "tenant_settings")),
) -> AuditLogPage:
    """Get paginated audit logs for current tenant. Admin only."""
    tenant_id = _get_tenant_or_raise(user)

    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    if action:
        query = query.where(AuditLog.action.startswith(action))
    if from_date:
        from datetime import datetime

        try:
            from_dt = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid 'from' date format. Use ISO 8601.",
            ) from None
        query = query.where(AuditLog.created_at >= from_dt)
    if to_date:
        from datetime import datetime

        try:
            to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid 'to' date format. Use ISO 8601.",
            ) from None
        query = query.where(AuditLog.created_at <= to_dt)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    # Fetch page
    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    entries = list(result.scalars().all())

    return AuditLogPage(
        items=[AuditLogEntry.model_validate(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )
