"""ClientInvite repository — thin data access layer."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.client_invite import ClientInvite


async def get_by_id(session: AsyncSession, invite_id: uuid.UUID) -> ClientInvite | None:
    """Fetch invite by primary key with client and tenant loaded in 1 query."""
    stmt = (
        select(ClientInvite)
        .options(joinedload(ClientInvite.client), joinedload(ClientInvite.tenant))
        .where(ClientInvite.id == invite_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> ClientInvite | None:
    """Fetch invite by SHA-256 token hash with client and tenant loaded in 1 query."""
    stmt = (
        select(ClientInvite)
        .options(joinedload(ClientInvite.client), joinedload(ClientInvite.tenant))
        .where(ClientInvite.token_hash == token_hash)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_client_id(
    session: AsyncSession,
    client_id: uuid.UUID,
) -> list[ClientInvite]:
    """List invites for a client, newest first."""
    stmt = (
        select(ClientInvite)
        .options(joinedload(ClientInvite.client), joinedload(ClientInvite.tenant))
        .where(ClientInvite.client_id == client_id)
        .order_by(ClientInvite.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


async def get_pending_by_client_and_email(
    session: AsyncSession,
    client_id: uuid.UUID,
    email: str,
) -> ClientInvite | None:
    """Fetch a pending (not accepted) invite by client + email."""
    from datetime import UTC, datetime

    stmt = (
        select(ClientInvite)
        .where(
            ClientInvite.client_id == client_id,
            ClientInvite.email == email,
            ClientInvite.accepted_at.is_(None),
            ClientInvite.expires_at > datetime.now(UTC),
        )
        .order_by(ClientInvite.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
