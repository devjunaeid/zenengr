"""Limit enforcement service.

Checks tenant resource usage against plan limits before create operations.
Raises LimitExceededError when limit would be exceeded.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.models.invite import Invite
from app.models.plan import Plan
from app.models.tenant import Tenant

Resource = Literal["admin_users", "clients", "active_projects", "storage_mb"]


class LimitExceededError(HTTPException):
    """Raised when a resource limit would be exceeded."""

    def __init__(self, resource: str, limit: int, current: int) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLAN_LIMIT_EXCEEDED",
                "message": f"Plan limit exceeded for {resource}",
                "details": {
                    "resource": resource,
                    "limit": limit,
                    "current": current,
                },
            },
        )


async def _get_plan_limits(session: AsyncSession, tenant_id: uuid.UUID) -> Plan:
    """Fetch tenant's plan. Raises 404 if tenant not found."""
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    plan = await session.get(Plan, tenant.plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found for tenant",
        )
    return plan


async def _count_current_usage(
    session: AsyncSession, tenant_id: uuid.UUID, resource: Resource
) -> int:
    """Count current usage for a given resource type."""
    if resource == "admin_users":
        # Active users + pending invites (not yet accepted)
        user_count = await _count_active_admin_users(session, tenant_id)
        invite_count = await _count_pending_invites(session, tenant_id)
        return user_count + invite_count
    if resource == "clients":
        from app.models.client import Client
        from app.models.enums import ClientStatus

        stmt = select(func.count()).where(
            Client.tenant_id == tenant_id,
            Client.status != ClientStatus.ARCHIVED,
        )
        result = await session.execute(stmt)
        return result.scalar_one()
    if resource == "active_projects":
        # TODO: wire to Project model when it lands
        return 0
    if resource == "storage_mb":
        # TODO: wire to storage tracking when it lands
        return 0
    return 0


async def _count_active_admin_users(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count()).where(
        AdminUser.tenant_id == tenant_id,
        AdminUser.is_active == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def _count_pending_invites(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    from datetime import UTC, datetime

    stmt = select(func.count()).where(
        Invite.tenant_id == tenant_id,
        Invite.accepted_at.is_(None),
        Invite.expires_at > datetime.now(UTC),
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def check_limit(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    resource: Resource,
    increment: int = 1,
) -> None:
    """Check if incrementing resource usage would exceed plan limit.

    Raises LimitExceededError (403) when current + increment > plan limit.
    Passes silently when under limit.
    """
    plan = await _get_plan_limits(session, tenant_id)

    # Alias legacy/alternative names
    normalized_resource = "admin_users" if resource in ("team_members", "users") else resource

    limit_map: dict[str, int] = {
        "admin_users": plan.max_admin_users,
        "clients": plan.max_clients,
        "active_projects": plan.max_active_projects,
        "storage_mb": plan.max_storage_mb,
    }
    limit = limit_map.get(normalized_resource, plan.max_admin_users)

    current = await _count_current_usage(session, tenant_id, normalized_resource)  # type: ignore[arg-type]
    if current + increment > limit:
        raise LimitExceededError(resource=resource, limit=limit, current=current)
