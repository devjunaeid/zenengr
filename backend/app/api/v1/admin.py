"""Super Admin platform APIs.

All endpoints require super_admin role (require_super_admin dependency).
Base path: /api/v1/admin
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_super_admin
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.enums import ActorType, AdminUserRole, TenantStatus
from app.schemas.admin import (
    PlanCreateRequest,
    PlanResponse,
    PlanUpdateRequest,
    SlugAvailableResponse,
    SubscriptionUpdateRequest,
    SubscriptionViewResponse,
    TenantCreateRequest,
    TenantCreateResponse,
    TenantDetailResponse,
    TenantListItem,
    TenantListResponse,
    TenantUpdateRequest,
)
from app.schemas.tenant import (
    AuditLogEntry,
    AuditLogPage,
    FeatureFlagDetail,
    FeatureFlagItem,
    FeatureFlagOverrideUpdate,
    PlanFlagDefaultUpdate,
    TenantSettingItem,
    TenantSettingUpdateRequest,
)
from app.services.plans import (
    create_plan,
    delete_plan,
    get_plan,
    list_plans,
    update_plan,
)
from app.services.tenants import (
    cancel_tenant,
    check_slug_available,
    create_tenant,
    get_subscription,
    get_tenant_detail,
    list_tenants,
    reactivate_tenant,
    suspend_tenant,
    update_subscription,
    update_tenant,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ═══════════════════════════════════════════════════════════════════════════
# Plans
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def api_create_plan(
    body: PlanCreateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> PlanResponse:
    """Create a new subscription plan."""
    plan = await create_plan(
        session,
        _admin.id,
        name=body.name,
        description=body.description,
        max_admin_users=body.max_admin_users,
        max_clients=body.max_clients,
        max_active_projects=body.max_active_projects,
        max_storage_mb=body.max_storage_mb,
    )
    tenant_count = 0
    from app.repositories.plans import count_tenants

    tenant_count = await count_tenants(session, plan.id)
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        max_admin_users=plan.max_admin_users,
        max_clients=plan.max_clients,
        max_active_projects=plan.max_active_projects,
        max_storage_mb=plan.max_storage_mb,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        tenant_count=tenant_count,
    )


@router.get("/plans", response_model=list[PlanResponse])
async def api_list_plans(
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> list[PlanResponse]:
    """List all plans with tenant count."""
    plans = await list_plans(session)
    return [PlanResponse(**p) for p in plans]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def api_get_plan(
    plan_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> PlanResponse:
    """Get plan detail."""
    try:
        uid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        ) from None
    plan = await get_plan(session, uid)
    return PlanResponse(**plan)


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def api_update_plan(
    plan_id: str,
    body: PlanUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> PlanResponse:
    """Update a plan."""
    try:
        uid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        ) from None
    plan = await update_plan(
        session,
        _admin.id,
        uid,
        name=body.name,
        description=body.description,
        max_admin_users=body.max_admin_users,
        max_clients=body.max_clients,
        max_active_projects=body.max_active_projects,
        max_storage_mb=body.max_storage_mb,
        is_active=body.is_active,
    )
    from app.repositories.plans import count_tenants

    tenant_count = await count_tenants(session, plan.id)
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        max_admin_users=plan.max_admin_users,
        max_clients=plan.max_clients,
        max_active_projects=plan.max_active_projects,
        max_storage_mb=plan.max_storage_mb,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        tenant_count=tenant_count,
    )


@router.delete("/plans/{plan_id}", status_code=status.HTTP_200_OK)
async def api_delete_plan(
    plan_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, str]:
    """Delete a plan. Soft if tenants assigned, hard otherwise."""
    try:
        uid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        ) from None
    await delete_plan(session, _admin.id, uid)
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════
# Tenants
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/tenants", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def api_create_tenant(
    body: TenantCreateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> TenantCreateResponse:
    """Provision a new tenant with subscription, settings, and admin user."""
    result = await create_tenant(
        session,
        _admin.id,
        business_name=body.business_name,
        slug=body.slug,
        plan_id=body.plan_id,
        admin_email=str(body.admin_email),
        admin_full_name=body.admin_full_name,
    )
    return TenantCreateResponse(**result)


@router.get("/tenants/slug-available", response_model=SlugAvailableResponse)
async def api_slug_available(
    slug: str = Query(..., min_length=1, max_length=255),
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> SlugAvailableResponse:
    """Check slug availability. Super admin only (not public)."""
    result = await check_slug_available(session, slug)
    return SlugAvailableResponse(**result)


@router.get("/tenants", response_model=TenantListResponse)
async def api_list_tenants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: TenantStatus | None = None,
    q: str | None = Query(default=None, min_length=1),
    sort: str | None = Query(default=None, pattern=r"^-?(business_name|created_at)$"),
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> TenantListResponse:
    """List tenants with pagination, filter, search, sort."""
    result = await list_tenants(
        session,
        page=page,
        page_size=page_size,
        status=status,
        q=q,
        sort=sort,
    )
    return TenantListResponse(
        items=[TenantListItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def api_get_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> TenantDetailResponse:
    """Get tenant detail with subscription and settings."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    result = await get_tenant_detail(session, uid)
    return TenantDetailResponse(**result)


@router.patch("/tenants/{tenant_id}", response_model=TenantDetailResponse)
async def api_update_tenant(
    tenant_id: str,
    body: TenantUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> TenantDetailResponse:
    """Update tenant profile fields. Slug is immutable."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    await update_tenant(
        session,
        _admin.id,
        uid,
        business_name=body.business_name,
        contact_info=body.contact_info,
        branding=body.branding,
        logo_url=body.logo_url,
    )
    # Return fresh detail
    result = await get_tenant_detail(session, uid)
    return TenantDetailResponse(**result)


@router.post("/tenants/{tenant_id}/suspend", status_code=status.HTTP_200_OK)
async def api_suspend_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, str]:
    """Suspend a tenant. Reversible."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    await suspend_tenant(session, _admin.id, uid)
    return {"status": "ok"}


@router.post("/tenants/{tenant_id}/reactivate", status_code=status.HTTP_200_OK)
async def api_reactivate_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, str]:
    """Reactivate a suspended or trial tenant."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    await reactivate_tenant(session, _admin.id, uid)
    return {"status": "ok"}


@router.post("/tenants/{tenant_id}/cancel", status_code=status.HTTP_200_OK)
async def api_cancel_tenant(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, str]:
    """Cancel a tenant. Irreversible in MVP."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    await cancel_tenant(session, _admin.id, uid)
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════
# Subscription
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/tenants/{tenant_id}/subscription", response_model=SubscriptionViewResponse)
async def api_get_subscription(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> SubscriptionViewResponse:
    """Get tenant subscription details."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    result = await get_subscription(session, uid)
    return SubscriptionViewResponse(**result)


@router.patch("/tenants/{tenant_id}/subscription", response_model=SubscriptionViewResponse)
async def api_update_subscription(
    tenant_id: str,
    body: SubscriptionUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> SubscriptionViewResponse:
    """Update tenant subscription (plan, status, billing cycle, renewal date)."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None
    result = await update_subscription(
        session,
        _admin.id,
        uid,
        plan_id=body.plan_id,
        subscription_status=body.status,
        billing_cycle=body.billing_cycle,
        renewal_date=body.renewal_date,
    )
    return SubscriptionViewResponse(**result)


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Settings (SA)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/tenants/{tenant_id}/settings", response_model=list[TenantSettingItem])
async def api_list_tenant_settings(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> list[TenantSettingItem]:
    """Get all settings for a tenant. SA sees all values unmasked."""
    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None

    from app.services.settings import get_tenant_settings

    items = await get_tenant_settings(session, uid, AdminUserRole.SUPER_ADMIN)
    return [TenantSettingItem(**item) for item in items]


@router.patch("/tenants/{tenant_id}/settings/{key}", response_model=TenantSettingItem)
async def api_update_tenant_setting(
    tenant_id: str,
    key: str,
    body: TenantSettingUpdateRequest,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> TenantSettingItem:
    """Update any setting for a tenant (SA bypasses permission level)."""
    from app.services.audit import log as audit_log
    from app.services.settings import (
        get_tenant_setting_by_key,
        update_tenant_setting,
    )

    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None

    result = await update_tenant_setting(session, uid, key, body.value)

    await audit_log(
        session,
        tenant_id=uid,
        actor_id=_admin.id,
        actor_type=ActorType.SUPER_ADMIN,
        action="tenant.setting_updated",
        entity_type="tenant_setting",
        entity_id=key,
        details={"key": key, "old_value": result["old_value"], "new_value": result["new_value"]},
    )

    updated = await get_tenant_setting_by_key(session, uid, key)
    return TenantSettingItem(
        key=key,
        value=updated.value if updated else None,
        permission_level=updated.permission_level.value if updated else "",
        editable=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tenant Feature Flags (SA management)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/tenants/{tenant_id}/flags", response_model=dict[str, Any])
async def api_list_tenant_flags(
    tenant_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    """Get resolved flags + raw overrides for a tenant."""
    from app.services.feature_flags import get_overrides_list, get_resolved_flags

    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None

    resolved = await get_resolved_flags(session, uid)
    overrides = await get_overrides_list(session, uid)
    return {"resolved": [FeatureFlagDetail(**r) for r in resolved], "overrides": overrides}


@router.put("/tenants/{tenant_id}/flags/{key}", status_code=status.HTTP_200_OK)
async def api_set_tenant_flag_override(
    tenant_id: str,
    key: str,
    body: FeatureFlagOverrideUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    """Set (upsert) a tenant-level feature flag override."""
    from app.services.audit import log as audit_log
    from app.services.feature_flags import set_override

    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None

    flag = await set_override(session, uid, key, body.enabled)

    await audit_log(
        session,
        tenant_id=uid,
        actor_id=_admin.id,
        actor_type=ActorType.SUPER_ADMIN,
        action="tenant.flag_set",
        entity_type="tenant_feature_flag",
        entity_id=str(flag.id),
        details={"key": key, "enabled": body.enabled},
    )

    return {"key": flag.key, "enabled": flag.enabled}


@router.delete("/tenants/{tenant_id}/flags/{key}", status_code=status.HTTP_200_OK)
async def api_remove_tenant_flag_override(
    tenant_id: str,
    key: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, str]:
    """Remove a tenant-level feature flag override (falls back to plan default)."""
    from app.services.audit import log as audit_log
    from app.services.feature_flags import remove_override

    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None

    await remove_override(session, uid, key)

    await audit_log(
        session,
        tenant_id=uid,
        actor_id=_admin.id,
        actor_type=ActorType.SUPER_ADMIN,
        action="tenant.flag_override_removed",
        entity_type="tenant_feature_flag",
        entity_id=key,
        details={"key": key},
    )

    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════
# Plan Flag Defaults (SA management)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/plans/{plan_id}/flags", response_model=list[FeatureFlagItem])
async def api_list_plan_flag_defaults(
    plan_id: str,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> list[FeatureFlagItem]:
    """Get plan-level feature flag defaults."""
    from app.services.feature_flags import get_plan_defaults

    try:
        uid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        ) from None

    defaults = await get_plan_defaults(session, uid)
    return [FeatureFlagItem(**d) for d in defaults]


@router.put("/plans/{plan_id}/flags/{key}", status_code=status.HTTP_200_OK)
async def api_set_plan_flag_default(
    plan_id: str,
    key: str,
    body: PlanFlagDefaultUpdate,
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> dict[str, Any]:
    """Set (upsert) a plan-level feature flag default.

    Existing tenant overrides persist (resolution order handles precedence).
    """
    from app.services.audit import log as audit_log
    from app.services.feature_flags import set_plan_default

    try:
        uid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        ) from None

    pd = await set_plan_default(session, uid, key, body.enabled)

    await audit_log(
        session,
        tenant_id=None,
        actor_id=_admin.id,
        actor_type=ActorType.SUPER_ADMIN,
        action="plan.flag_default_set",
        entity_type="plan_feature_default",
        entity_id=str(pd.id),
        details={"plan_id": str(uid), "key": key, "enabled": body.enabled},
    )

    return {"key": pd.key, "enabled": pd.enabled}


# ═══════════════════════════════════════════════════════════════════════════
# Audit Logs (SA views)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/tenants/{tenant_id}/audit-logs", response_model=AuditLogPage)
async def api_list_tenant_audit_logs(
    tenant_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, min_length=1),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> AuditLogPage:
    """Get paginated audit logs for a specific tenant. SA only."""
    from sqlalchemy import func, select

    try:
        uid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found"
        ) from None

    query = select(AuditLog).where(AuditLog.tenant_id == uid)

    if action:
        query = query.where(AuditLog.action.startswith(action))
    if from_date:
        from datetime import datetime

        try:
            from_dt = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid 'from' date format",
            ) from None
        query = query.where(AuditLog.created_at >= from_dt)
    if to_date:
        from datetime import datetime

        try:
            to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid 'to' date format",
            ) from None
        query = query.where(AuditLog.created_at <= to_dt)

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

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


@router.get("/audit-logs", response_model=AuditLogPage)
async def api_list_platform_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    action: str | None = Query(default=None, min_length=1),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_session),
    _admin: AdminUser = Depends(require_super_admin),
) -> AuditLogPage:
    """Get paginated platform-scope audit logs (tenant_id is null). SA only."""
    from sqlalchemy import func, select

    query = select(AuditLog).where(AuditLog.tenant_id.is_(None))

    if action:
        query = query.where(AuditLog.action.startswith(action))
    if from_date:
        from datetime import datetime

        try:
            from_dt = datetime.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid 'from' date format",
            ) from None
        query = query.where(AuditLog.created_at >= from_dt)
    if to_date:
        from datetime import datetime

        try:
            to_dt = datetime.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid 'to' date format",
            ) from None
        query = query.where(AuditLog.created_at <= to_dt)

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

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
