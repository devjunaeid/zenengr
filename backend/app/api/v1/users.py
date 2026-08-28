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
from app.schemas.roles import UserRoleUpdateRequest
from app.schemas.users import (
    AdminSetUserPasswordRequest,
    AdminUserCreateRequest,
    ResetPasswordRequest,
    UserListItem,
    UserListResponse,
)
from app.services import roles as role_service
from app.services.audit import log as audit_log
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
    search: str | None = None,
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
        search=search,
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


@tenant_router.post("/users", response_model=UserListItem, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminUserCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> UserListItem:
    """Create a new employee/staff member directly with email, password, and role."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    # 1. Plan limit check
    from app.services.limits import check_limit

    await check_limit(session, current_user.tenant_id, "admin_users")

    # 2. Password policy validation
    from app.services.password_policy import get_min_password_length, validate_password_policy

    min_length = await get_min_password_length(session, current_user.tenant_id)
    validate_password_policy(body.password, min_length)

    # 3. Email uniqueness check
    normalized_email = body.email.lower().strip()
    existing = await admin_user_repo.get_by_email(session, normalized_email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    # 4. Resolve role
    target_role = AdminUserRole.EMPLOYEE
    target_role_id = None
    if body.role_id:
        from app.models.role import Role

        try:
            r_uuid = uuid.UUID(body.role_id)
            r = await session.get(Role, r_uuid)
            if r and (r.tenant_id is None or r.tenant_id == current_user.tenant_id):
                target_role_id = r.id
                try:
                    target_role = AdminUserRole(r.name)
                except ValueError:
                    target_role = AdminUserRole.EMPLOYEE
        except ValueError:
            pass

    # 5. Create user
    new_user = AdminUser(
        tenant_id=current_user.tenant_id,
        email=normalized_email,
        full_name=body.full_name.strip(),
        hashed_password=hash_password(body.password),
        role=target_role,
        role_id=target_role_id,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()

    # 6. Default role fallback if role_id not set
    if new_user.role_id is None:
        await role_service.attach_default_role(session, new_user)
        await session.flush()

    # 7. Audit log
    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.created",
        entity_type="admin_user",
        entity_id=str(new_user.id),
        details={"email": normalized_email, "role": new_user.role.value},
    )

    await session.commit()
    return UserListItem(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
    )



@tenant_router.patch("/users/{user_id}/role", status_code=status.HTTP_200_OK)
async def change_user_role(
    user_id: str,
    body: UserRoleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str | None]:
    """Change an admin user's role by role_id. Last-admin guard applies."""
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

    await role_service.assign_user_role(
        session,
        tenant_id=current_user.tenant_id,
        target_user_id=target.id,
        role_id=body.role_id,
        actor_id=current_user.id,
    )

    return {
        "status": "ok",
        "role": target.role.value,
        "role_id": str(target.role_id) if target.role_id else None,
        "role_name": target.role_ref.name if target.role_ref else None,
    }


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
    await send_reset_email(session, target, raw_token)

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


@tenant_router.post("/users/{user_id}/set-password", status_code=status.HTTP_200_OK)
async def admin_set_password(
    user_id: str,
    body: AdminSetUserPasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str]:
    """Admin directly sets a new password for an employee."""
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

    # Validate password policy
    from app.services.password_policy import get_min_password_length, validate_password_policy

    min_length = await get_min_password_length(session, current_user.tenant_id)
    validate_password_policy(body.password, min_length)

    target.hashed_password = hash_password(body.password)
    await session.flush()

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.password_reset_by_admin",
        entity_type="admin_user",
        entity_id=str(target.id),
        details={"email": target.email},
    )

    await session.commit()
    return {"status": "ok"}


@tenant_router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> dict[str, str]:
    """Archive / Delete an employee from the tenant. Last-admin guard applies."""
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

    # Cannot delete self
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Cannot delete yourself",
        )

    # Last-admin guard
    if target.role == AdminUserRole.ADMIN:
        try:
            await ensure_not_last_admin(session, current_user.tenant_id, target.id)
        except LastAdminError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="user.archived",
        entity_type="admin_user",
        entity_id=str(target.id),
        details={"email": target.email, "full_name": target.full_name},
    )

    await session.delete(target)
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
