"""ClientUser repository — thin data access layer."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.client_user import ClientUser


async def get_by_email(session: AsyncSession, email: str) -> ClientUser | None:
    """Fetch client user by email with client relationship."""
    stmt = (
        select(ClientUser)
        .options(joinedload(ClientUser.client), joinedload(ClientUser.tenant))
        .where(ClientUser.email == email.lower().strip())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> ClientUser | None:
    """Fetch client user by primary key with client + tenant relationships."""
    stmt = (
        select(ClientUser)
        .options(joinedload(ClientUser.client), joinedload(ClientUser.tenant))
        .where(ClientUser.id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_client_id(
    session: AsyncSession,
    client_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ClientUser], int]:
    """List client users for a client, paginated."""
    query = select(ClientUser).where(ClientUser.client_id == client_id)

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(ClientUser.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def check_email_exists(session: AsyncSession, email: str) -> bool:
    """Check if any client user exists with this email (global unique)."""
    stmt = select(func.count()).where(ClientUser.email == email.lower().strip())
    result = await session.execute(stmt)
    return result.scalar_one() > 0
