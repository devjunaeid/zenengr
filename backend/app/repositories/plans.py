"""Plan repository — thin data access layer."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.tenant import Tenant


async def get_by_id(session: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    """Fetch plan by primary key."""
    stmt = select(Plan).where(Plan.id == plan_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_name(session: AsyncSession, name: str) -> Plan | None:
    """Fetch plan by exact name."""
    stmt = select(Plan).where(Plan.name == name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_all(session: AsyncSession) -> list[Plan]:
    """List all plans ordered by name."""
    stmt = select(Plan).order_by(Plan.name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create(session: AsyncSession, **kwargs: Any) -> Plan:
    """Create a new plan."""
    plan = Plan(**kwargs)
    session.add(plan)
    await session.flush()
    await session.refresh(plan)
    return plan


async def update(session: AsyncSession, plan: Plan, **kwargs: Any) -> Plan:
    """Update plan fields in-place."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(plan, key, value)
    await session.flush()
    await session.refresh(plan)
    return plan


async def delete(session: AsyncSession, plan: Plan) -> None:
    """Hard delete a plan."""
    await session.delete(plan)
    await session.flush()


async def count_tenants(session: AsyncSession, plan_id: uuid.UUID) -> int:
    """Count tenants assigned to a plan."""
    stmt = select(func.count()).select_from(Tenant).where(Tenant.plan_id == plan_id)
    result = await session.execute(stmt)
    return result.scalar_one()
