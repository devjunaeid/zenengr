"""Self-service account operations (FEAT-011).

Profile management, password change/reset, notification preferences,
email change + verification, and activity history for admin (staff
portal) and client portal users.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
import zoneinfo
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from pydantic import EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.admin_user import AdminUser
from app.models.client_password_reset_token import ClientPasswordResetToken
from app.models.client_user import ClientUser
from app.models.email_verification_token import EmailVerificationToken
from app.models.enums import ActorType
from app.models.user_activity import UserActivity
from app.repositories import admin_users as admin_user_repo
from app.repositories import client_users as client_user_repo
from app.services.audit import log as audit_log
from app.services.password_policy import get_min_password_length, validate_password_policy
from app.services.smtp import send_tenant_email
from app.services.users import create_password_reset_token
from app.storage import get_storage

# ── Helpers ────────────────────────────────────────────────────────────────


async def _record_activity(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
    tenant_id: uuid.UUID | None,
    event_type: str,
    description: str,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    """Append a UserActivity row (no commit)."""
    entry = UserActivity(
        user_id=user_id,
        user_type=user_type,
        tenant_id=tenant_id,
        event_type=event_type,
        description=description,
        old_value=old_value,
        new_value=new_value,
    )
    session.add(entry)


def _validate_timezone(value: str) -> None:
    try:
        zoneinfo.ZoneInfo(value)
    except (ValueError, TypeError, zoneinfo.ZoneInfoNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Invalid timezone '{value}'. "
                "Must be IANA timezone name (e.g. UTC, America/New_York)."
            ),
        ) from None


def _apply_profile_changes(
    user: AdminUser | ClientUser, changes: dict[str, str | None]
) -> list[str]:
    """Apply profile changes in-place. Returns list of changed keys."""
    changed_keys: list[str] = []
    for key, val in changes.items():
        old = getattr(user, key)
        if old != val:
            setattr(user, key, val)
            changed_keys.append(key)
    return changed_keys


# ── Email change (TODO-110) ────────────────────────────────────────────────


async def _request_email_change(
    session: AsyncSession,
    *,
    user: AdminUser | ClientUser,
    email: str,
    is_client: bool,
) -> bool:
    """Set pending_email and send a single-use verification email.

    The old email stays active until the token is consumed. Raises 409 if
    the requested email belongs to another user of the same type. Returns
    True when a change was requested (new email != current email).
    """
    new_email = email.lower().strip()
    if new_email == user.email.lower():
        return False

    other: AdminUser | ClientUser | None
    if is_client:
        other = await client_user_repo.get_by_email(session, new_email)
    else:
        other = await admin_user_repo.get_by_email(session, new_email)
    if other is not None and other.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )

    user.pending_email = new_email

    user_type = "client_user" if is_client else "admin_user"

    # Invalidate previous unused verification tokens for this user
    await session.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.user_type == user_type,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
    )

    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.password_reset_ttl_hours)

    token = EmailVerificationToken(
        user_id=user.id,
        user_type=user_type,
        new_email=new_email,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()

    portal_base_url = (
        settings.client_portal_base_url if is_client else settings.admin_portal_base_url
    )
    subject = "Verify your new email"
    body = (
        f"Confirm your new email address: "
        f"{portal_base_url}/verify-email?token={raw_token}\n\n"
        f"This link expires in {settings.password_reset_ttl_hours} hours."
    )
    await send_tenant_email(
        session,
        tenant_id=user.tenant_id,
        to=new_email,
        subject=subject,
        body=body,
    )
    return True


async def _verify_email(session: AsyncSession, *, token: str, user_type: str) -> None:
    """Consume a verification token; apply the pending email change."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await session.execute(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.user_type == user_type,
        )
    )
    verify_token = result.scalar_one_or_none()
    if verify_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification token not found",
        )
    if verify_token.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Verification token has expired",
        )
    if verify_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification token has already been used",
        )

    is_client = user_type == "client_user"
    user: AdminUser | ClientUser | None
    if is_client:
        user = await client_user_repo.get_by_id(session, verify_token.user_id)
    else:
        user = await admin_user_repo.get_by_id(session, verify_token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Re-check uniqueness of the pending email (could have been taken since)
    new_email = verify_token.new_email
    other: AdminUser | ClientUser | None
    if is_client:
        other = await client_user_repo.get_by_email(session, new_email)
    else:
        other = await admin_user_repo.get_by_email(session, new_email)
    if other is not None and other.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )

    old_email = user.email
    user.email = new_email
    user.pending_email = None
    verify_token.used_at = datetime.now(UTC)
    await session.flush()

    entity_type = "client_user" if is_client else "admin_user"
    actor_type = ActorType.CLIENT_USER if is_client else ActorType.ADMIN_USER

    await audit_log(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_type=actor_type,
        action="user.email_changed",
        entity_type=entity_type,
        entity_id=str(user.id),
        details={"old_email": old_email, "new_email": new_email},
    )
    await _record_activity(
        session,
        user_id=user.id,
        user_type=user_type,
        tenant_id=user.tenant_id,
        event_type="email.changed",
        description="Email changed",
        old_value=old_email,
        new_value=new_email,
    )
    await session.commit()


async def verify_email_admin(session: AsyncSession, *, token: str) -> None:
    """Verify a pending admin email change (TODO-110)."""
    await _verify_email(session, token=token, user_type="admin_user")


async def verify_email_client(session: AsyncSession, *, token: str) -> None:
    """Verify a pending client email change (TODO-110)."""
    await _verify_email(session, token=token, user_type="client_user")


# ── Profile ─────────────────────────────────────────────────────────────────


async def update_admin_profile(
    session: AsyncSession,
    *,
    user: AdminUser,
    full_name: str | None = None,
    avatar_url: str | None = None,
    phone: str | None = None,
    timezone: str | None = None,
    language: str | None = None,
    email: EmailStr | None = None,
) -> AdminUser:
    """Update admin user profile fields. None = unchanged; "" clears a value.

    email triggers the pending-verification flow: the current email stays
    active, the new one is set as pending_email until the token is consumed.
    """
    changes: dict[str, str | None] = {}
    if full_name is not None:
        changes["full_name"] = full_name
    if avatar_url is not None:
        changes["avatar_url"] = avatar_url
    if phone is not None:
        changes["phone"] = phone
    if timezone is not None:
        _validate_timezone(timezone)
        changes["timezone"] = timezone
    if language is not None:
        changes["language"] = language

    changed_keys = _apply_profile_changes(user, changes)

    email_change_requested = False
    if email is not None:
        email_change_requested = await _request_email_change(
            session, user=user, email=email, is_client=False
        )

    if changed_keys or email_change_requested:
        await session.flush()

        audit_keys = list(changed_keys)
        details: dict[str, object] = {"changed_keys": audit_keys}
        if email_change_requested:
            audit_keys.append("email")
            details["pending_email"] = str(user.pending_email)
            description = "Email change requested, pending verification"
        else:
            description = f"Profile updated: {', '.join(changed_keys)}"

        await audit_log(
            session,
            tenant_id=user.tenant_id,
            actor_id=user.id,
            actor_type=ActorType.ADMIN_USER,
            action="user.profile_updated",
            entity_type="admin_user",
            entity_id=str(user.id),
            details=details,
        )
        await _record_activity(
            session,
            user_id=user.id,
            user_type="admin_user",
            tenant_id=user.tenant_id,
            event_type="profile.updated",
            description=description,
        )
        await session.commit()

    await session.refresh(user)
    return user


async def update_client_profile(
    session: AsyncSession,
    *,
    user: ClientUser,
    full_name: str | None = None,
    avatar_url: str | None = None,
    phone: str | None = None,
    timezone: str | None = None,
    language: str | None = None,
    email: EmailStr | None = None,
) -> ClientUser:
    """Update client user profile fields. None = unchanged; "" clears a value.

    email triggers the pending-verification flow: the current email stays
    active, the new one is set as pending_email until the token is consumed.
    """
    changes: dict[str, str | None] = {}
    if full_name is not None:
        changes["full_name"] = full_name
    if avatar_url is not None:
        changes["avatar_url"] = avatar_url
    if phone is not None:
        changes["phone"] = phone
    if timezone is not None:
        _validate_timezone(timezone)
        changes["timezone"] = timezone
    if language is not None:
        changes["language"] = language

    changed_keys = _apply_profile_changes(user, changes)

    email_change_requested = False
    if email is not None:
        email_change_requested = await _request_email_change(
            session, user=user, email=email, is_client=True
        )

    if changed_keys or email_change_requested:
        await session.flush()

        audit_keys = list(changed_keys)
        details: dict[str, object] = {"changed_keys": audit_keys}
        if email_change_requested:
            audit_keys.append("email")
            details["pending_email"] = str(user.pending_email)
            description = "Email change requested, pending verification"
        else:
            description = f"Profile updated: {', '.join(changed_keys)}"

        await audit_log(
            session,
            tenant_id=user.tenant_id,
            actor_id=user.id,
            actor_type=ActorType.CLIENT_USER,
            action="user.profile_updated",
            entity_type="client_user",
            entity_id=str(user.id),
            details=details,
        )
        await _record_activity(
            session,
            user_id=user.id,
            user_type="client_user",
            tenant_id=user.tenant_id,
            event_type="profile.updated",
            description=description,
        )
        await session.commit()

    await session.refresh(user)
    return user


_ALLOWED_AVATAR_TYPES = {
    "image/png": ".png",
    "image/x-png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
_MAX_AVATAR_BYTES = 5 * 1024 * 1024


async def save_user_avatar(
    session: AsyncSession,
    *,
    user: AdminUser | ClientUser,
    filename: str,
    content_type: str,
    data: bytes,
    is_client: bool,
) -> str:
    """Validate image bytes, store avatar under public/avatars, update user.avatar_url, and audit."""
    content_type = (content_type or "").lower()
    fname = (filename or "").lower()
    if content_type not in _ALLOWED_AVATAR_TYPES and fname:
        if fname.endswith(".png"):
            content_type = "image/png"
        elif fname.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif fname.endswith(".webp"):
            content_type = "image/webp"
        elif fname.endswith(".gif"):
            content_type = "image/gif"

    ext = _ALLOWED_AVATAR_TYPES.get(content_type)
    if ext is None:
        raise ValueError("Unsupported image type. Use PNG, JPEG, WebP, or GIF.")

    if len(data) > _MAX_AVATAR_BYTES:
        raise ValueError("Avatar image too large (max 5MB)")

    file_token = uuid.uuid4().hex[:8]
    storage_key = f"public/avatars/{user.id}_{file_token}{ext}"
    await get_storage().put(storage_key, data, content_type)

    avatar_url = f"/uploads/avatars/{user.id}_{file_token}{ext}"
    user.avatar_url = avatar_url

    await session.flush()
    actor_type = ActorType.CLIENT_USER if is_client else ActorType.ADMIN_USER
    entity_type = "client_user" if is_client else "admin_user"
    user_type = "client_user" if is_client else "admin_user"

    await audit_log(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_type=actor_type,
        action="user.avatar_updated",
        entity_type=entity_type,
        entity_id=str(user.id),
        details={"avatar_url": avatar_url},
    )
    await _record_activity(
        session,
        user_id=user.id,
        user_type=user_type,
        tenant_id=user.tenant_id,
        event_type="profile.updated",
        description="Profile picture updated",
    )
    await session.commit()
    await session.refresh(user)
    return avatar_url


async def delete_user_avatar(
    session: AsyncSession,
    *,
    user: AdminUser | ClientUser,
    is_client: bool,
) -> None:
    """Remove user's avatar_url, audit the change."""
    if user.avatar_url is None:
        return
    user.avatar_url = None
    await session.flush()
    actor_type = ActorType.CLIENT_USER if is_client else ActorType.ADMIN_USER
    entity_type = "client_user" if is_client else "admin_user"
    user_type = "client_user" if is_client else "admin_user"

    await audit_log(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_type=actor_type,
        action="user.avatar_deleted",
        entity_type=entity_type,
        entity_id=str(user.id),
        details={},
    )
    await _record_activity(
        session,
        user_id=user.id,
        user_type=user_type,
        tenant_id=user.tenant_id,
        event_type="profile.updated",
        description="Profile picture removed",
    )
    await session.commit()
    await session.refresh(user)


# ── Password change ─────────────────────────────────────────────────────────


async def change_password(
    session: AsyncSession,
    *,
    user: AdminUser | ClientUser,
    current_password: str,
    new_password: str,
    min_length: int,
) -> None:
    """Verify current password, apply policy, update password hash."""
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current password is incorrect",
        )

    validate_password_policy(new_password, min_length)

    user.hashed_password = hash_password(new_password)
    await session.flush()

    is_client = isinstance(user, ClientUser)
    actor_type = ActorType.CLIENT_USER if is_client else ActorType.ADMIN_USER
    entity_type = "client_user" if is_client else "admin_user"

    await audit_log(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_type=actor_type,
        action="user.password_changed",
        entity_type=entity_type,
        entity_id=str(user.id),
    )
    await _record_activity(
        session,
        user_id=user.id,
        user_type=entity_type,
        tenant_id=user.tenant_id,
        event_type="password.changed",
        description="Password changed",
    )
    await session.commit()


# ── Forgot password ─────────────────────────────────────────────────────────


async def forgot_password_admin(session: AsyncSession, *, email: str) -> None:
    """Send self-service password reset email for an admin user.

    Unknown email -> no-op (always 200, no existence leak).
    """
    user = await admin_user_repo.get_by_email(session, email)
    if user is None:
        return

    _, raw_token = await create_password_reset_token(session, user, created_by=user)

    settings = get_settings()
    reset_url = f"{settings.admin_portal_base_url}/reset-password?token={raw_token}"
    subject = "Password reset request"
    body = (
        f"We received a request to reset your password for your ZenEngr account.\n\n"
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

    await session.commit()


async def forgot_password_client(session: AsyncSession, *, email: str) -> None:
    """Send self-service password reset email for a client user.

    Unknown email -> no-op (always 200, no existence leak).
    """
    user = await client_user_repo.get_by_email(session, email)
    if user is None:
        return

    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.password_reset_ttl_hours)

    # Invalidate previous unused tokens for this client user
    await session.execute(
        update(ClientPasswordResetToken)
        .where(
            ClientPasswordResetToken.client_user_id == user.id,
            ClientPasswordResetToken.used_at.is_(None),
        )
        .values(used_at=datetime.now(UTC))
    )

    token = ClientPasswordResetToken(
        client_user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()

    reset_url = f"{settings.client_portal_base_url}/reset-password?token={raw_token}"
    subject = "Password reset request"
    body = (
        f"We received a request to reset your password for your client portal account.\n\n"
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

    await session.commit()


async def reset_client_password(session: AsyncSession, *, token: str, new_password: str) -> None:
    """Consume a client password reset token and set a new password."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await session.execute(
        select(ClientPasswordResetToken).where(ClientPasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()
    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset token not found",
        )
    if reset_token.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Reset token has expired",
        )
    if reset_token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reset token has already been used",
        )

    user = await client_user_repo.get_by_id(session, reset_token.client_user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    min_length = await get_min_password_length(session, user.tenant_id)
    validate_password_policy(new_password, min_length)

    user.hashed_password = hash_password(new_password)
    reset_token.used_at = datetime.now(UTC)
    await session.flush()

    await audit_log(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_type=ActorType.CLIENT_USER,
        action="user.password_reset_completed",
        entity_type="client_user",
        entity_id=str(user.id),
    )
    await session.commit()


# ── Activity ────────────────────────────────────────────────────────────────


async def list_activity(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[UserActivity]:
    """List the caller's activity entries, newest first."""
    stmt = (
        select(UserActivity)
        .where(UserActivity.user_id == user_id)
        .order_by(UserActivity.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
