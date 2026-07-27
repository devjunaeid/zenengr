"""Authentication service layer.

Handles login verification, tenant gate checks, and token issuance.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.models.admin_user import AdminUser
from app.models.enums import AdminUserRole, TenantStatus
from app.repositories import admin_users as admin_user_repo


class AuthenticationError(Exception):
    """Generic auth failure (401)."""


class AccountDeactivatedError(AuthenticationError):
    """User is deactivated."""


class TenantSuspendedError(AuthenticationError):
    """Tenant is suspended or cancelled (403)."""


class TenantCancelledError(AuthenticationError):
    """Tenant is cancelled (403)."""


_LOGIN_FAILED_MSG = "Invalid credentials"


async def authenticate_admin(
    session: AsyncSession, email: str, password: str
) -> tuple[str, str, AdminUser]:
    """Verify credentials and issue access token.

    Returns: (access_token, token_type, user).
    Raises AuthenticationError subclass on failure.
    """
    user = await admin_user_repo.get_by_email(session, email)

    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError(_LOGIN_FAILED_MSG)

    # Check user active
    if not user.is_active:
        raise AccountDeactivatedError(_LOGIN_FAILED_MSG)

    # Tenant gate for non-super_admin users
    if user.role != AdminUserRole.SUPER_ADMIN:
        tenant = user.tenant
        if tenant is None:
            raise AuthenticationError(_LOGIN_FAILED_MSG)
        if tenant.status == TenantStatus.SUSPENDED:
            raise TenantSuspendedError("Account suspended. Contact your administrator.")
        if tenant.status == TenantStatus.CANCELLED:
            raise TenantCancelledError("Account cancelled. Contact your administrator.")
        # Trial and Active are OK

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role=user.role.value,
        realm="admin",
    )

    return token, "bearer", user
