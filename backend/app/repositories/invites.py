"""Invite repository — thin data access layer."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invite import Invite


async def get_by_id(session: AsyncSession, invite_id: uuid.UUID) -> Invite | None:
    """Fetch invite by primary key with tenant eager-loaded."""
    stmt = select(Invite).options(selectinload(Invite.tenant)).where(Invite.id == invite_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_tenant_id(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> list[Invite]:
    """List invites for a tenant, newest first, paginated."""
    offset = (page - 1) * page_size
    stmt = (
        select(Invite)
        .where(Invite.tenant_id == tenant_id)
        .order_by(Invite.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> Invite | None:
    """Fetch invite by SHA-256 token hash with tenant eager-loaded."""
    stmt = select(Invite).options(selectinload(Invite.tenant)).where(Invite.token == token_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_any_by_email_and_tenant(
    session: AsyncSession, email: str, tenant_id: uuid.UUID
) -> Invite | None:
    """Fetch any invite (any status) by email + tenant."""
    stmt = select(Invite).where(Invite.email == email, Invite.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
