"""Tenant-scoped service catalog endpoints.

Base path: /api/v1/tenant/services
Guards: manage/services = admin+manager for writes; all staff can read.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.schemas.services import (
    MilestoneStepResponse,
    ServiceCreateRequest,
    ServiceDetailResponse,
    ServiceListItem,
    ServiceListResponse,
    ServiceUpdateRequest,
)
from app.services import services as service_service

router = APIRouter(prefix="/tenant/services", tags=["services"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _to_detail_response(service: Any) -> ServiceDetailResponse:
    return ServiceDetailResponse(
        id=service.id,
        name=service.name,
        description=service.description,
        default_price=service.default_price,
        is_active=service.is_active,
        step_count=len(service.milestone_steps),
        created_at=service.created_at,
        updated_at=service.updated_at,
        steps=[
            MilestoneStepResponse.model_validate(s) for s in service.milestone_steps
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=ServiceDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_endpoint(
    body: ServiceCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "services")),
) -> ServiceDetailResponse:
    """Create a new service with optional milestone step templates. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    service = await service_service.create_service(
        session,
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        default_price=body.default_price,
        is_active=True,
        steps=body.steps,
        actor_id=user.id,
    )
    return _to_detail_response(service)


@router.get("/", response_model=ServiceListResponse)
async def list_services_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1),
    sort: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ServiceListResponse:
    """List services for a tenant. All staff can read."""
    tenant_id = _get_tenant_id(user)

    result = await service_service.list_services(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        q=q,
        sort=sort,
    )

    items = [ServiceListItem(**item) for item in result["items"]]
    return ServiceListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{service_id}", response_model=ServiceDetailResponse)
async def get_service_endpoint(
    service_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ServiceDetailResponse:
    """Get service detail with milestone step templates. All staff can read."""
    tenant_id = _get_tenant_id(user)

    try:
        sid = uuid.UUID(service_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        ) from None

    service = await service_service.get_service_detail(
        session, tenant_id=tenant_id, service_id=sid
    )
    return _to_detail_response(service)


@router.patch("/{service_id}", response_model=ServiceDetailResponse)
async def update_service_endpoint(
    service_id: str,
    body: ServiceUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "services")),
) -> ServiceDetailResponse:
    """Update service fields. If `steps` provided, replaces full set. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)

    try:
        sid = uuid.UUID(service_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        ) from None

    updates = body.model_dump(exclude_unset=True)

    service = await service_service.update_service(
        session,
        tenant_id=tenant_id,
        service_id=sid,
        updates=updates,
        actor_id=user.id,
    )
    return _to_detail_response(service)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_service_endpoint(
    service_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "services")),
) -> None:
    """Hard-delete a service. Cascades to step templates. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)

    try:
        sid = uuid.UUID(service_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        ) from None

    await service_service.delete_service(
        session, tenant_id=tenant_id, service_id=sid, actor_id=user.id
    )
