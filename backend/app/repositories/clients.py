"""Client repository -- thin data access layer."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.enums import ClientStatus


async def get_by_id(session: AsyncSession, client_id: uuid.UUID) -> Client | None:
    """Fetch client by primary key."""
    stmt = select(Client).where(Client.id == client_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id_with_users(session: AsyncSession, client_id: uuid.UUID) -> Client | None:
    """Fetch client by id with client_users eager-loaded."""
    stmt = select(Client).options(selectinload(Client.client_users)).where(Client.id == client_id)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def get_by_tenant_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client | None:
    """Fetch client by id scoped to a tenant. None if not found or wrong tenant."""
    stmt = select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_tenant_id_with_users(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client | None:
    """Fetch client by id scoped to tenant with client_users eager-loaded."""
    stmt = (
        select(Client)
        .options(selectinload(Client.client_users))
        .where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def create(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    client_type: Any,
    email: str | None = None,
    phone: str | None = None,
    billing_address: dict[str, Any] | None = None,
    tax_id: str | None = None,
    tags: list[str] | None = None,
) -> Client:
    """Create a new client."""
    client = Client(
        tenant_id=tenant_id,
        name=name,
        client_type=client_type,
        email=email,
        phone=phone,
        billing_address=billing_address or {},
        tax_id=tax_id,
        tags=tags or [],
    )
    session.add(client)
    await session.flush()
    await session.refresh(client)
    return client


async def list_paginated(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: ClientStatus | None = None,
    q: str | None = None,
    tag: str | None = None,
    sort: str | None = None,
) -> tuple[list[Client], int]:
    """List clients for a tenant with filtering, search, sort, pagination."""
    query = select(Client).where(Client.tenant_id == tenant_id)

    if status is not None:
        query = query.where(Client.status == status)

    if q:
        query = query.where(Client.name.ilike(f"%{q}%"))

    if tag:
        from sqlalchemy import text

        query = query.where(Client.tags.op("@>")(text(f"'[\"{tag}\"]'::jsonb")))

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    # Sort
    if sort:
        desc = sort.startswith("-")
        col_name = sort.lstrip("-")
        col = getattr(Client, col_name, None)
        if col is not None:
            query = query.order_by(col.desc() if desc else col.asc())
        else:
            query = query.order_by(Client.name.asc())
    else:
        query = query.order_by(Client.name.asc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def count_non_archived(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Count active (non-archived) clients for a tenant."""
    stmt = select(func.count()).where(
        Client.tenant_id == tenant_id,
        Client.status != ClientStatus.ARCHIVED,
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def update(session: AsyncSession, client: Client, **kwargs: Any) -> Client:
    """Update client fields. Caller must flush."""
    for key, val in kwargs.items():
        setattr(client, key, val)
    await session.flush()
    await session.refresh(client)
    return client
