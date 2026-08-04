"""User administration endpoints: list, role edit, de/reactivate, reset password."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.core.security import hash_password
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import ActorType, AdminUserRole
from app.repositories import admin_users as admin_user_repo
from app.repositories import password_reset_tokens as token_repo
from app.schemas.users import (
    ResetPasswordRequest,
    RoleChangeRequest,
    UserListItem,
    UserListResponse,
)
from app.services.audit import log as audit_log
from app.services.email import create_email_sender
from app.services.users import (
    LastAdminError,
    create_password_reset_token,
    ensure_not_last_admin,
    send_reset_email,
)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Tenant-scoped (admin: manage admin_users; manager: view admin_users) ──

tenant_router = APIRouter(prefix="/tenant", tags=["users"])

# ── Public (no auth required) ──────────────────────────────────────────────

public_router = APIRouter(prefix="/auth", tags=["auth"])


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_tenant_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> AdminUser:
    """Fetch user scoped to tenant. 404 if not found or different tenant.

    Avoids user-existence leaks across tenants.
    """
    target = await admin_user_repo.get_by_id(session, user_id)
    if target is None or target.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return target


# ── Tenant endpoints ───────────────────────────────────────────────────────


@tenant_router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
    role: AdminUserRole | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("view", "admin_users")),
) -> UserListResponse:
    """List tenant's staff users with optional filters. Available to Admin + Manager."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    items, total = await admin_user_repo.get_by_tenant_id(
        session,
        current_user.tenant_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        role=role,
    )

    return UserListResponse(
        items=[
            UserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=u.role,
                is_active=u.is_active,
                created_at=u.created_at,
            )
            for u in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@tenant_router.patch("/users/{user_id}/role", status_code=status.HTTP_200_OK)
async def change_user_role(
    user_id: str,
    body: RoleChangeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str]:
    """Change an admin user's role. Last-admin guard applies."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    try:
        target_uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    target = await _get_tenant_user(session, target_uid, current_user.tenant_id)

    # Cannot change own role
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot change your own role",
        )

    old_role = target.role
    new_role = body.role

    # Last-admin guard: if changing away from Admin, check not last
    if old_role == AdminUserRole.ADMIN and new_role != AdminUserRole.ADMIN:
        try:
            await ensure_not_last_admin(session, current_user.tenant_id, target.id)
        except LastAdminError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    target.role = new_role
    await session.flush()

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.role_changed",
        entity_type="admin_user",
        entity_id=str(target.id),
        details={"from": old_role.value, "to": new_role.value},
    )

    await session.commit()
    return {"status": "ok"}


@tenant_router.post("/users/{user_id}/deactivate", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str]:
    """Deactivate an admin user. Last-admin guard applies."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    try:
        target_uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    target = await _get_tenant_user(session, target_uid, current_user.tenant_id)

    # Cannot deactivate self
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot deactivate yourself",
        )

    # Already inactive
    if not target.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already deactivated",
        )

    # Last-admin guard for admin deactivation
    if target.role == AdminUserRole.ADMIN:
        try:
            await ensure_not_last_admin(session, current_user.tenant_id, target.id)
        except LastAdminError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    target.is_active = False
    await session.flush()

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.deactivated",
        entity_type="admin_user",
        entity_id=str(target.id),
    )

    await session.commit()
    return {"status": "ok"}


@tenant_router.post("/users/{user_id}/reactivate", status_code=status.HTTP_200_OK)
async def reactivate_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str]:
    """Reactivate a deactivated admin user."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    try:
        target_uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    target = await _get_tenant_user(session, target_uid, current_user.tenant_id)

    # Already active
    if target.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already active",
        )

    target.is_active = True
    await session.flush()

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.reactivated",
        entity_type="admin_user",
        entity_id=str(target.id),
    )

    await session.commit()
    return {"status": "ok"}


@tenant_router.post("/users/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def admin_reset_password(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str]:
    """Admin-triggered password reset for an active admin user."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    try:
        target_uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        ) from None

    target = await _get_tenant_user(session, target_uid, current_user.tenant_id)

    # Target must be active
    if not target.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot reset password for a deactivated user",
        )

    # Create token + invalidate old ones
    token_obj, raw_token = await create_password_reset_token(session, target, current_user)

    # Send email
    email_sender = create_email_sender()
    await send_reset_email(email_sender, target, raw_token)

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.password_reset_initiated",
        entity_type="admin_user",
        entity_id=str(target.id),
    )

    await session.commit()
    return {"status": "ok"}


# ── Public endpoints ───────────────────────────────────────────────────────


@public_router.post("/reset-password", status_code=status.HTTP_200_OK)
async def consume_password_reset(
    body: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Consume a password reset token and set new password.

    This is the public consume endpoint (no auth required). The request
    endpoint (admin-triggered) is a separate tenant-scoped endpoint.
    """
    token_hash = _hash_token(body.token)
    token = await token_repo.get_by_token_hash(session, token_hash)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset token not found",
        )

    if token.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Reset token has expired",
        )

    if token.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reset token has already been used",
        )

    # Password policy (tenant-configurable, TODO-115)
    user = await admin_user_repo.get_by_id(session, token.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    from app.services.password_policy import get_min_password_length, validate_password_policy

    min_length = await get_min_password_length(session, user.tenant_id)
    validate_password_policy(body.new_password, min_length)

    user.hashed_password = hash_password(body.new_password)

    # Mark token used
    await token_repo.mark_used(session, token.id)

    # Invalidate all other unused tokens for this user
    await token_repo.mark_all_unused_for_user(session, token.user_id)

    await audit_log(
        session,
        tenant_id=user.tenant_id,
        actor_id=user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.password_reset_completed",
        entity_type="admin_user",
        entity_id=str(user.id),
    )

    await session.commit()
    return {"status": "ok"}
