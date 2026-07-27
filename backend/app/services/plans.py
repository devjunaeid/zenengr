"""Plan service — business logic for plan CRUD."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorType
from app.models.plan import Plan
from app.repositories import plans as plan_repo
from app.services.audit import log as audit_log


async def create_plan(
    session: AsyncSession,
    actor_id: uuid.UUID,
    *,
    name: str,
    description: str,
    max_admin_users: int,
    max_clients: int,
    max_active_projects: int,
    max_storage_mb: int,
) -> Plan:
    """Create a new plan. Raises 409 on duplicate name."""
    existing = await plan_repo.get_by_name(session, name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A plan named '{name}' already exists",
        )

    plan = await plan_repo.create(
        session,
        name=name,
        description=description,
        max_admin_users=max_admin_users,
        max_clients=max_clients,
        max_active_projects=max_active_projects,
        max_storage_mb=max_storage_mb,
    )

    await audit_log(
        session,
        tenant_id=None,
        actor_id=actor_id,
        actor_type=ActorType.SUPER_ADMIN,
        action="plan.created",
        entity_type="plan",
        entity_id=str(plan.id),
        details={"name": plan.name},
    )

    return plan


async def list_plans(session: AsyncSession) -> list[dict[str, Any]]:
    """List all plans with tenant count."""
    plans = await plan_repo.list_all(session)
    result: list[dict[str, Any]] = []
    for plan in plans:
        tenant_count = await plan_repo.count_tenants(session, plan.id)
        result.append(
            {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "max_admin_users": plan.max_admin_users,
                "max_clients": plan.max_clients,
                "max_active_projects": plan.max_active_projects,
                "max_storage_mb": plan.max_storage_mb,
                "is_active": plan.is_active,
                "created_at": plan.created_at,
                "updated_at": plan.updated_at,
                "tenant_count": tenant_count,
            }
        )
    return result


async def get_plan(session: AsyncSession, plan_id: uuid.UUID) -> dict[str, Any]:
    """Get plan detail with tenant count."""
    plan = await plan_repo.get_by_id(session, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    tenant_count = await plan_repo.count_tenants(session, plan.id)
    return {
        "id": plan.id,
        "name": plan.name,
        "description": plan.description,
        "max_admin_users": plan.max_admin_users,
        "max_clients": plan.max_clients,
        "max_active_projects": plan.max_active_projects,
        "max_storage_mb": plan.max_storage_mb,
        "is_active": plan.is_active,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "tenant_count": tenant_count,
    }


async def update_plan(
    session: AsyncSession,
    actor_id: uuid.UUID,
    plan_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    max_admin_users: int | None = None,
    max_clients: int | None = None,
    max_active_projects: int | None = None,
    max_storage_mb: int | None = None,
    is_active: bool | None = None,
) -> Plan:
    """Update a plan. Raises 404 if not found, 409 on name conflict."""
    plan = await plan_repo.get_by_id(session, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    if name is not None and name != plan.name:
        existing = await plan_repo.get_by_name(session, name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A plan named '{name}' already exists",
            )

    kwargs = {
        "name": name,
        "description": description,
        "max_admin_users": max_admin_users,
        "max_clients": max_clients,
        "max_active_projects": max_active_projects,
        "max_storage_mb": max_storage_mb,
        "is_active": is_active,
    }
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    plan = await plan_repo.update(session, plan, **filtered)

    await audit_log(
        session,
        tenant_id=None,
        actor_id=actor_id,
        actor_type=ActorType.SUPER_ADMIN,
        action="plan.updated",
        entity_type="plan",
        entity_id=str(plan.id),
        details={"updated_fields": list(filtered.keys())},
    )

    return plan


async def delete_plan(session: AsyncSession, actor_id: uuid.UUID, plan_id: uuid.UUID) -> None:
    """Delete a plan. Raises 409 if tenants are assigned (soft only).

    If tenants exist, raise conflict. Otherwise hard delete.
    """
    plan = await plan_repo.get_by_id(session, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    tenant_count = await plan_repo.count_tenants(session, plan.id)
    if tenant_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete plan with {tenant_count} assigned tenant(s). "
            f"Deactivate the plan instead.",
        )

    await plan_repo.delete(session, plan)

    await audit_log(
        session,
        tenant_id=None,
        actor_id=actor_id,
        actor_type=ActorType.SUPER_ADMIN,
        action="plan.deleted",
        entity_type="plan",
        entity_id=str(plan.id),
        details={"name": plan.name},
    )
