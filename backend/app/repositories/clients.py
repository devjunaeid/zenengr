"""Client repository — thin data access layer."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client


async def get_by_id(session: AsyncSession, client_id: uuid.UUID) -> Client | None:
    """Fetch client by primary key."""
    stmt = select(Client).where(Client.id == client_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_tenant_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client | None:
    """Fetch client by id scoped to a tenant. None if not found or wrong tenant."""
    stmt = select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
