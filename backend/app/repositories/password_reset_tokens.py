"""PasswordResetToken repository — thin data access layer."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


async def get_by_token_hash(session: AsyncSession, token_hash: str) -> PasswordResetToken | None:
    """Fetch token by SHA-256 hash."""
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_unused_by_user(session: AsyncSession, user_id: uuid.UUID) -> list[PasswordResetToken]:
    """Fetch all unused (non-expired, non-consumed) tokens for a user."""
    from datetime import UTC, datetime

    stmt = select(PasswordResetToken).where(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at > datetime.now(UTC),
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_used(session: AsyncSession, token_id: uuid.UUID) -> None:
    """Mark a token as consumed."""
    from datetime import UTC, datetime

    stmt = (
        update(PasswordResetToken)
        .where(PasswordResetToken.id == token_id)
        .values(used_at=datetime.now(UTC))
    )
    await session.execute(stmt)


async def mark_all_unused_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Mark all unused tokens for a user as used (invalidation)."""
    from datetime import UTC, datetime

    stmt = (
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
    )
    await session.execute(stmt)
