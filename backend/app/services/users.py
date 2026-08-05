"""User administration service layer."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.admin_user import AdminUser
from app.models.password_reset_token import PasswordResetToken
from app.repositories import admin_users as admin_user_repo
from app.repositories import password_reset_tokens as token_repo
from app.services.smtp import send_tenant_email

# ── Last-admin guard ────────────────────────────────────────────────────


class LastAdminError(ValueError):
    """Raised when operation would leave tenant with zero active Admins."""


async def ensure_not_last_admin(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    """Raise LastAdminError if action would leave tenant with <1 active Admin.

    Checks: if target is an active Admin, count other active Admins in tenant.
    If count == 0, the action is blocked.
    """
    count = await admin_user_repo.count_active_admins(
        session, tenant_id, exclude_user_id=target_user_id
    )
    if count == 0:
        raise LastAdminError("Cannot remove the last active Admin of the tenant")


# ── Password reset helpers ──────────────────────────────────────────────


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_password_reset_token(
    session: AsyncSession,
    user: AdminUser,
    created_by: AdminUser,
) -> tuple[PasswordResetToken, str]:
    """Create a new password reset token. Invalidates previous unused tokens.

    Returns (token_obj, raw_token_string).
    """
    # Invalidate old unused tokens for this user
    await token_repo.mark_all_unused_for_user(session, user.id)

    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.password_reset_ttl_hours)

    token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_by=created_by.id,
    )
    session.add(token)
    await session.flush()

    return token, raw_token


async def send_reset_email(
    session: AsyncSession,
    user: AdminUser,
    raw_token: str,
) -> None:
    """Send admin-triggered password reset email."""
    settings = get_settings()
    reset_url = f"{settings.admin_portal_base_url}/reset-password?token={raw_token}"
    subject = "Your administrator initiated a password reset"
    body = (
        f"Your administrator has initiated a password reset for your account.\n\n"
        f"Click the link below to reset your password:\n\n"
        f"{reset_url}\n\n"
        f"This link expires in {settings.password_reset_ttl_hours} hours."
    )
    await send_tenant_email(
        session,
        tenant_id=user.tenant_id,
        to=user.email,
        subject=subject,
        body=body,
    )
