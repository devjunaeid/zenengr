"""Tenant-scoped role management endpoints (FEAT-016, TODO-163).

Base path: /api/v1/tenant/roles
Guards: manage/roles = admin+manager for writes; all staff can read
(list + catalog are open to any authenticated tenant staff).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.schemas.roles import (
    PermissionCatalogItem,
    RoleCreateRequest,
    RolePermissionResponse,
    RoleResponse,
    RoleUpdateRequest,
)
from app.services import roles as role_service

router = APIRouter(prefix="/tenant/roles", tags=["roles"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        ) from exc


def _to_role_response(role: Any) -> RoleResponse:
    permissions = [
        RolePermissionResponse(action=p.action, resource=p.resource, granted=p.granted)
        for p in sorted(role.permissions, key=lambda p: (p.action, p.resource))
    ]
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        tenant_id=role.tenant_id,
        permissions=permissions,
    )


@router.get("/", response_model=list[RoleResponse])
async def list_roles_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[RoleResponse]:
    """List system roles + this tenant's custom roles. All staff can read."""
    tenant_id = _get_tenant_id(user)
    roles = await role_service.list_roles(session, tenant_id=tenant_id)
    return [_to_role_response(r) for r in roles]


@router.get("/permissions", response_model=list[PermissionCatalogItem])
async def get_permission_catalog_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[PermissionCatalogItem]:
    """Return the full action/resource catalog (label + group). All staff can read."""
    _ = user
    return [PermissionCatalogItem(**item) for item in role_service.get_permission_catalog()]


@router.post(
    "/",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_endpoint(
    body: RoleCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "roles")),
) -> RoleResponse:
    """Create a tenant custom role with its granted permissions."""
    tenant_id = _get_tenant_id(user)
    role = await role_service.create_role(
        session,
        tenant_id=tenant_id,
        name=body.name,
        description=body.description,
        permissions=body.permissions,
        actor_id=user.id,
    )
    return _to_role_response(role)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role_endpoint(
    role_id: str,
    body: RoleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "roles")),
) -> RoleResponse:
    """Update a role (system permission sets or custom role fields)."""
    tenant_id = _get_tenant_id(user)
    rid = _parse_uuid(role_id)
    role = await role_service.update_role(
        session,
        tenant_id=tenant_id,
        role_id=rid,
        name=body.name,
        description=body.description,
        permissions=body.permissions,
        actor_id=user.id,
    )
    return _to_role_response(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_endpoint(
    role_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "roles")),
) -> Response:
    """Delete a tenant custom role (unassigned only)."""
    tenant_id = _get_tenant_id(user)
    rid = _parse_uuid(role_id)
    await role_service.delete_role(
        session,
        tenant_id=tenant_id,
        role_id=rid,
        actor_id=user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{role_id}/reset", response_model=RoleResponse)
async def reset_role_defaults_endpoint(
    role_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "roles")),
) -> RoleResponse:
    """Reset a system role (manager/employee) to its seeded permission set."""
    tenant_id = _get_tenant_id(user)
    rid = _parse_uuid(role_id)
    role = await role_service.reset_role_defaults(
        session,
        tenant_id=tenant_id,
        role_id=rid,
        actor_id=user.id,
    )
    return _to_role_response(role)
