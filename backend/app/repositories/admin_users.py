"""AdminUser repository — thin data access layer."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.admin_user import AdminUser
from app.models.enums import AdminUserRole


async def get_by_email(session: AsyncSession, email: str) -> AdminUser | None:
    """Fetch admin user by email (case-insensitive via lowered storage)."""
    stmt = (
        select(AdminUser)
        .options(joinedload(AdminUser.tenant))
        .where(AdminUser.email == email.lower().strip())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> AdminUser | None:
    """Fetch admin user by primary key with tenant relationship in single query."""
    stmt = select(AdminUser).options(joinedload(AdminUser.tenant)).where(AdminUser.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_tenant_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
    role: AdminUserRole | None = None,
) -> tuple[list[AdminUser], int]:
    """List admin users for a tenant with optional filters. Returns (items, total)."""
    query = select(AdminUser).where(AdminUser.tenant_id == tenant_id)

    if is_active is not None:
        query = query.where(AdminUser.is_active == is_active)
    if role is not None:
        query = query.where(AdminUser.role == role)

    # Total count
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(AdminUser.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def count_active_admins(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    exclude_user_id: uuid.UUID | None = None,
) -> int:
    """Count active Admin users in a tenant, optionally excluding one user."""
    stmt = select(func.count()).where(
        AdminUser.tenant_id == tenant_id,
        AdminUser.role == AdminUserRole.ADMIN,
        AdminUser.is_active == True,  # noqa: E712
    )
    if exclude_user_id is not None:
        stmt = stmt.where(AdminUser.id != exclude_user_id)
    result = await session.execute(stmt)
    return result.scalar_one()
