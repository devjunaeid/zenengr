"""FastAPI dependency injection for auth and authorization.

Provides:
- get_current_admin_user: decodes JWT, loads user, enforces realm, tenant gate
- get_current_client_user: decodes JWT, loads client user, enforces realm, gates
- require_roles: role-based access (403)
- require_permission: permission-based access (403)
- require_super_admin: super admin platform check (403)
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, decode_access_token
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.client_user import ClientUser
from app.models.enums import AdminUserRole, TenantStatus
from app.models.role import Role
from app.repositories import admin_users as admin_user_repo
from app.services.permissions import has_permission, role_has_permission

import time

_security_scheme = HTTPBearer()

_USER_CACHE: dict[uuid.UUID, tuple[float, AdminUser]] = {}


def invalidate_user_cache(user_id: uuid.UUID | None = None) -> None:
    """Clear cached admin user (called on user or role mutation)."""
    if user_id is not None:
        _USER_CACHE.pop(user_id, None)
    else:
        _USER_CACHE.clear()


async def get_current_admin_user(
    session: AsyncSession = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Depends(_security_scheme),
) -> AdminUser:
    """Decode JWT, load user from DB (with short TTL cache), enforce realm and tenant gate."""
    try:
        payload: TokenPayload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.realm != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token realm",
        )

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc

    now = time.monotonic()
    cached = _USER_CACHE.get(user_id)
    if cached is not None and now < cached[0] and cached[1].is_active:
        user = cached[1]
    else:
        user = await admin_user_repo.get_by_id(session, user_id)
        if user is not None and user.is_active:
            _USER_CACHE[user_id] = (now + 60.0, user)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Tenant gate for non-super_admin (TODO-009)
    if user.role != AdminUserRole.SUPER_ADMIN:
        tenant = user.tenant
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        if tenant.status == TenantStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account suspended. Contact your administrator.",
            )
        if tenant.status == TenantStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account cancelled. Contact your administrator.",
            )

    return user


async def get_current_client_user(
    session: AsyncSession = Depends(get_session),
    credentials: HTTPAuthorizationCredentials = Depends(_security_scheme),
) -> ClientUser:
    """Decode client-realm JWT, load client user, enforce gates."""
    from app.repositories import client_users as client_user_repo

    try:
        payload: TokenPayload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.realm != "client":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token realm",
        )

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc

    user = await client_user_repo.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Client archived check
    from app.models.enums import ClientStatus

    client = user.client
    if client is None or client.status == ClientStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client account archived",
        )

    # Tenant gate
    tenant = user.tenant
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if tenant.status == TenantStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact your administrator.",
        )
    if tenant.status == TenantStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account cancelled. Contact your administrator.",
        )

    return user


def require_roles(*roles: AdminUserRole) -> type:
    """Dependency factory: requires user to have one of the given roles."""

    async def _role_checker(
        user: AdminUser = Depends(get_current_admin_user),
    ) -> AdminUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _role_checker  # type: ignore[return-value]


def require_permission(action: str, resource: str) -> type:
    """Dependency factory: requires action on resource per RBAC matrix.

    Super admin bypasses tenant permission check — use require_super_admin
    for platform endpoints instead.

    Users with a role_id are checked against their DB-backed role row
    (role_permissions, cached per role); legacy users (role_id NULL) fall
    back to the static matrix in app/services/permissions.py.
    """

    async def _permission_checker(
        session: AsyncSession = Depends(get_session),
        user: AdminUser = Depends(get_current_admin_user),
    ) -> AdminUser:
        # Super admin and tenant admin have full access; bypass extra DB queries
        if user.role in (AdminUserRole.SUPER_ADMIN, AdminUserRole.ADMIN):
            return user

        role: Role | None = None
        if user.role_id is not None:
            role = await session.get(Role, user.role_id)

        if role is None:
            # Legacy: no role row (or row vanished) -> static matrix fallback
            if not has_permission(user.role, action, resource):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            return user

        if not await role_has_permission(session, role=role, action=action, resource=resource):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _permission_checker  # type: ignore[return-value]


async def require_super_admin(
    user: AdminUser = Depends(get_current_admin_user),
) -> AdminUser:
    """Dependency: user must be super_admin (403 otherwise)."""
    if user.role != AdminUserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return user


def require_feature_flag(key: str) -> type:
    """Dependency factory: gates endpoint on feature flag for caller's tenant.

    Super admin is exempt (platform scope has no tenant flags).
    Returns 403 with code FEATURE_DISABLED when flag disabled.
    """

    async def _flag_checker(
        session: AsyncSession = Depends(get_session),
        user: AdminUser = Depends(get_current_admin_user),
    ) -> AdminUser:
        if user.role == AdminUserRole.SUPER_ADMIN:
            return user
        if user.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User must belong to a tenant",
            )
        from app.services.feature_flags import is_feature_enabled

        enabled = await is_feature_enabled(session, user.tenant_id, key)
        if not enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FEATURE_DISABLED",
                    "message": f"Feature '{key}' is not enabled for your tenant",
                    "details": {"flag": key},
                },
            )
        return user

    return _flag_checker  # type: ignore[return-value]
