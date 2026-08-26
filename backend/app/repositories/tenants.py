"""Tenant repository — thin data access layer."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.admin_user import AdminUser
from app.models.enums import TenantStatus
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription


async def get_by_id(
    session: AsyncSession, tenant_id: uuid.UUID, *, load_relations: bool = False
) -> Tenant | None:
    """Fetch tenant by primary key."""
    stmt = select(Tenant)
    if load_relations:
        stmt = stmt.options(
            joinedload(Tenant.plan),
            joinedload(Tenant.subscription),
            joinedload(Tenant.settings),
        )
    stmt = stmt.where(Tenant.id == tenant_id)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def get_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    """Fetch tenant by slug."""
    stmt = select(Tenant).where(Tenant.slug == slug)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create(session: AsyncSession, **kwargs: Any) -> Tenant:
    """Create a new tenant."""
    tenant = Tenant(**kwargs)
    session.add(tenant)
    await session.flush()
    await session.refresh(tenant)
    return tenant


async def update(session: AsyncSession, tenant: Tenant, **kwargs: Any) -> Tenant:
    """Update tenant fields in-place."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(tenant, key, value)
    await session.flush()
    await session.refresh(tenant)
    return tenant


async def list_paginated(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status: TenantStatus | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[Tenant], int]:
    """List tenants with pagination, filtering, search, and sorting.

    Returns (items, total).
    """
    query = select(Tenant).options(
        joinedload(Tenant.plan),
        joinedload(Tenant.subscription),
    )

    count_q = select(func.count(Tenant.id))

    if status is not None:
        query = query.where(Tenant.status == status)
        count_q = count_q.where(Tenant.status == status)
    if q:
        pattern = f"%{q}%"
        query = query.where(or_(Tenant.business_name.ilike(pattern), Tenant.slug.ilike(pattern)))
        count_q = count_q.where(or_(Tenant.business_name.ilike(pattern), Tenant.slug.ilike(pattern)))

    # Total count
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    if total == 0:
        return [], 0

    # Sort
    if sort == "business_name":
        query = query.order_by(Tenant.business_name.asc())
    elif sort == "-business_name":
        query = query.order_by(Tenant.business_name.desc())
    elif sort == "-created_at":
        query = query.order_by(Tenant.created_at.desc())
    else:
        query = query.order_by(Tenant.created_at.asc())

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def count_active_users(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Count active admin users in a tenant."""
    stmt = select(func.count()).where(
        AdminUser.tenant_id == tenant_id,
        AdminUser.is_active == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_subscription(session: AsyncSession, **kwargs: Any) -> TenantSubscription:
    """Create a tenant subscription."""
    sub = TenantSubscription(**kwargs)
    session.add(sub)
    await session.flush()
    await session.refresh(sub)
    return sub


async def get_subscription_by_tenant_id(
    session: AsyncSession, tenant_id: uuid.UUID
) -> TenantSubscription | None:
    """Get subscription for a tenant."""
    stmt = (
        select(TenantSubscription)
        .options(selectinload(TenantSubscription.tenant))
        .where(TenantSubscription.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_subscription(
    session: AsyncSession, sub: TenantSubscription, **kwargs: Any
) -> TenantSubscription:
    """Update subscription fields in-place."""
    for key, value in kwargs.items():
        if value is not None:
            setattr(sub, key, value)
    await session.flush()
    await session.refresh(sub)
    return sub
