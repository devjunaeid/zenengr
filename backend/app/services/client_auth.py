"""Client portal authentication service layer."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.models.client_user import ClientUser
from app.models.enums import ActorType, ClientStatus, TenantStatus
from app.repositories import client_users as client_user_repo


class AuthenticationError(Exception):
    """Generic auth failure (401)."""


class AccountDeactivatedError(AuthenticationError):
    """User is deactivated."""


class ClientArchivedError(AuthenticationError):
    """Client is archived (403)."""


class TenantSuspendedError(AuthenticationError):
    """Tenant is suspended (403)."""


class TenantCancelledError(AuthenticationError):
    """Tenant is cancelled (403)."""


_LOGIN_FAILED_MSG = "Invalid credentials"


async def authenticate_client_user(
    session: AsyncSession, email: str, password: str
) -> tuple[str, str, ClientUser]:
    """Verify client user credentials and issue client-realm JWT.

    Returns: (access_token, token_type, user).
    Raises AuthenticationError subclass on failure.
    """
    user = await client_user_repo.get_by_email(session, email)

    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationError(_LOGIN_FAILED_MSG)

    if not user.is_active:
        raise AccountDeactivatedError(_LOGIN_FAILED_MSG)

    # Client archived check
    client = user.client
    if client is None:
        raise AuthenticationError(_LOGIN_FAILED_MSG)

    if client.status == ClientStatus.ARCHIVED:
        raise ClientArchivedError("Client account archived")

    # Tenant gate
    tenant = user.tenant
    if tenant is None:
        raise AuthenticationError(_LOGIN_FAILED_MSG)
    if tenant.status == TenantStatus.SUSPENDED:
        raise TenantSuspendedError("Account suspended. Contact your administrator.")
    if tenant.status == TenantStatus.CANCELLED:
        raise TenantCancelledError("Account cancelled. Contact your administrator.")

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role="client_user",
        realm="client",
        client_id=str(user.client_id),
    )

    return token, "bearer", user


class InviteExpiredError(ValueError):
    """Invite has expired."""


class InviteAlreadyAcceptedError(ValueError):
    """Invite already accepted."""


class ClientUserEmailExistsError(ValueError):
    """Email already in use by another client user."""


async def register_client_user_from_invite(
    session: AsyncSession,
    token: str,
    full_name: str,
    password: str,
) -> tuple[str, str, ClientUser]:
    """Register client user from valid invite. Returns auto-login JWT."""
    from app.core.security import hash_password
    from app.models.client_user import ClientUser
    from app.repositories import client_invites as invite_repo
    from app.services.audit import log as audit_log

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invite = await invite_repo.get_by_token_hash(session, token_hash)

    if invite is None:
        raise ValueError("Invite not found")

    if invite.accepted_at is not None:
        raise InviteAlreadyAcceptedError("This invite has already been accepted")

    if invite.expires_at < datetime.now(UTC):
        raise InviteExpiredError("Invite has expired")

    # Password policy (tenant-configurable, TODO-115)
    from app.services.password_policy import get_min_password_length, validate_password_policy

    min_length = await get_min_password_length(session, invite.tenant_id)
    validate_password_policy(password, min_length)

    # Check email not already used globally
    email_exists = await client_user_repo.check_email_exists(session, invite.email)
    if email_exists:
        raise ClientUserEmailExistsError("A client user with this email already exists")

    # Create client user
    new_user = ClientUser(
        client_id=invite.client_id,
        tenant_id=invite.tenant_id,
        email=invite.email,
        full_name=full_name,
        hashed_password=hash_password(password),
        is_active=True,
        is_primary_billing_contact=False,
    )
    session.add(new_user)
    await session.flush()

    # Mark invite accepted
    invite.accepted_at = datetime.now(UTC)

    # Audit
    await audit_log(
        session,
        tenant_id=invite.tenant_id,
        actor_id=new_user.id,
        actor_type=ActorType.CLIENT_USER,
        action="client_user.registered",
        entity_type="client_user",
        entity_id=str(new_user.id),
        details={"invite_id": str(invite.id), "client_id": str(invite.client_id)},
    )

    await session.commit()
    await session.refresh(new_user)

    # Auto-login
    token_jwt = create_access_token(
        user_id=str(new_user.id),
        tenant_id=str(new_user.tenant_id),
        role="client_user",
        realm="client",
        client_id=str(new_user.client_id),
    )

    return token_jwt, "bearer", new_user
