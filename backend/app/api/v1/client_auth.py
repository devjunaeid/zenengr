"""Client Portal auth and invite endpoints."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_client_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.client_invite import ClientInvite
from app.models.client_user import ClientUser
from app.models.enums import ActorType
from app.repositories import client_invites as invite_repo
from app.repositories import client_users as client_user_repo
from app.repositories import clients as client_repo
from app.schemas.client_auth import (
    ClientInviteCreateRequest,
    ClientInviteLookupResponse,
    ClientInviteResponse,
    ClientLoginRequest,
    ClientLoginResponse,
    ClientMeResponse,
    ClientProfileUpdateRequest,
    ClientRegisterRequest,
    ClientSummary,
    ClientUserResponse,
)
from app.services.audit import log as audit_log
from app.services.client_auth import (
    AccountDeactivatedError,
    AuthenticationError,
    ClientArchivedError,
    ClientUserEmailExistsError,
    InviteAlreadyAcceptedError,
    InviteExpiredError,
    TenantCancelledError,
    TenantSuspendedError,
    authenticate_client_user,
    register_client_user_from_invite,
)
from app.services.email import EmailSender, create_email_sender

# ── Tenant-scoped (admin: manage clients) ────────────────────────────────

tenant_router = APIRouter(prefix="/tenant", tags=["client-invites"])

# ── Public (no auth required) ──────────────────────────────────────────────

public_router = APIRouter(prefix="/client/auth", tags=["client-auth"])

# ── Authenticated client portal ────────────────────────────────────────────

auth_router = APIRouter(prefix="/client/auth", tags=["client-auth"])


# ── Helpers ────────────────────────────────────────────────────────────────


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _derive_status(invite: ClientInvite) -> str:
    if invite.accepted_at is not None:
        return "accepted"
    if invite.expires_at < datetime.now(UTC):
        return "expired"
    return "pending"


async def _send_client_invite_email(
    email_sender: EmailSender,
    tenant_name: str,
    client_name: str,
    email: str,
    raw_token: str,
) -> None:
    """Send client user invitation email with accept link."""
    settings = get_settings()
    accept_url = f"{settings.client_portal_base_url}/accept-invite?token={raw_token}"
    subject = f"You're invited to access {client_name}"
    body = (
        f"You've been invited by {tenant_name} to access client portal for {client_name}.\n\n"
        f"Click the link below to accept the invitation and set up your account:\n\n"
        f"{accept_url}\n\n"
        f"This link expires in {settings.invite_ttl_hours} hours."
    )
    await email_sender.send_email(to=email, subject=subject, body=body)


# ═══════════════════════════════════════════════════════════════════════════
# Public auth endpoints
# ═══════════════════════════════════════════════════════════════════════════


@public_router.post("/login", response_model=ClientLoginResponse)
async def client_login(
    body: ClientLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> ClientLoginResponse:
    """Authenticate client user, return client-realm JWT + user profile."""
    try:
        token, token_type, user = await authenticate_client_user(session, body.email, body.password)
    except ClientArchivedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (TenantSuspendedError, TenantCancelledError) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (AuthenticationError, AccountDeactivatedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return ClientLoginResponse(
        access_token=token,
        token_type=token_type,
        user=ClientUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role="client_user",
            client_id=str(user.client_id),
            tenant_id=str(user.tenant_id),
        ),
    )


@public_router.get("/invite/{token}", response_model=ClientInviteLookupResponse)
async def lookup_client_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> ClientInviteLookupResponse:
    """Look up invite by raw token. 404/410/409 semantics."""
    token_hash = _hash_token(token)
    invite = await invite_repo.get_by_token_hash(session, token_hash)

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found",
        )

    if invite.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This invite has already been accepted",
        )

    if invite.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invite expired; ask your admin to resend",
        )

    return ClientInviteLookupResponse(
        email=invite.email,
        client_name=invite.client.name if invite.client else "Unknown",
        tenant_name=invite.tenant.business_name if invite.tenant else "Unknown",
        expires_at=invite.expires_at,
    )


@public_router.post("/register", response_model=ClientLoginResponse)
async def register_client_user(
    body: ClientRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> ClientLoginResponse:
    """Register client user from valid invite. Returns auto-login JWT."""
    if len(body.password) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be at least 10 characters",
        )

    try:
        token, token_type, user = await register_client_user_from_invite(
            session, body.token, body.full_name, body.password
        )
    except InviteAlreadyAcceptedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except InviteExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc
    except ClientUserEmailExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        # Either "Invite not found" or password policy
        msg = str(exc)
        if "10 characters" in msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        ) from exc

    return ClientLoginResponse(
        access_token=token,
        token_type=token_type,
        user=ClientUserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role="client_user",
            client_id=str(user.client_id),
            tenant_id=str(user.tenant_id),
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Authenticated client portal endpoints
# ═══════════════════════════════════════════════════════════════════════════


@auth_router.get("/me", response_model=ClientMeResponse)
async def client_me(
    user: ClientUser = Depends(get_current_client_user),
) -> ClientMeResponse:
    """Return authenticated client user profile + client summary."""
    client = user.client
    tenant = user.tenant
    return ClientMeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role="client_user",
        client_id=str(user.client_id),
        tenant_id=str(user.tenant_id),
        tenant_name=tenant.business_name if tenant else None,
        client=ClientSummary(
            id=str(client.id) if client else None,
            name=client.name if client else "Unknown",
            status=client.status.value if client else "unknown",
            email=client.email if client else None,
            phone=client.phone if client else None,
            billing_address=client.billing_address if client else None,
            tax_id=client.tax_id if client else None,
        ),
    )


@auth_router.patch("/profile", response_model=ClientMeResponse)
async def update_client_profile_endpoint(
    body: ClientProfileUpdateRequest,
    user: ClientUser = Depends(get_current_client_user),
    session: AsyncSession = Depends(get_session),
) -> ClientMeResponse:
    """Client self-service: update contact details (email, phone) only.

    tax_id, billing_address, name are forbidden -> 422 via extra="forbid".
    """
    from app.services.clients import update_client_profile

    client = await update_client_profile(
        session,
        tenant_id=user.tenant_id,
        client_id=user.client_id,
        email=body.email,
        phone=body.phone,
        actor_id=user.id,
    )

    tenant = user.tenant
    return ClientMeResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role="client_user",
        client_id=str(user.client_id),
        tenant_id=str(user.tenant_id),
        tenant_name=tenant.business_name if tenant else None,
        client=ClientSummary(
            id=str(client.id),
            name=client.name,
            status=client.status.value,
            email=client.email,
            phone=client.phone,
            billing_address=client.billing_address,
            tax_id=client.tax_id,
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tenant-scoped invite management endpoints
# ═══════════════════════════════════════════════════════════════════════════


@tenant_router.post(
    "/clients/{client_id}/invites",
    response_model=ClientInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_client_invite(
    client_id: str,
    body: ClientInviteCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "clients")),
) -> ClientInviteResponse:
    """Create client user invite. Resends if pending invite exists."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    import uuid

    try:
        client_uid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    # Verify client exists in this tenant
    client = await client_repo.get_by_tenant_id(session, current_user.tenant_id, client_uid)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    email = body.email.lower().strip()

    # Check if active client user with this email already exists (global unique)
    email_exists = await client_user_repo.check_email_exists(session, email)
    if email_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client user with this email already exists",
        )

    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.invite_ttl_hours)

    # Check for existing pending invite for this client + email
    existing_invite = await invite_repo.get_pending_by_client_and_email(session, client_uid, email)

    if existing_invite is not None:
        # Regenerate token + reset expiry (resend path)
        existing_invite.token_hash = token_hash
        existing_invite.expires_at = expires_at
        existing_invite.accepted_at = None
        invite = existing_invite

        await audit_log(
            session,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.id,
            actor_type=ActorType.ADMIN_USER,
            action="client_user.invite_resent",
            entity_type="client_invite",
            entity_id=str(invite.id),
        )
    else:
        invite = ClientInvite(
            tenant_id=current_user.tenant_id,
            client_id=client_uid,
            email=email,
            token_hash=token_hash,
            expires_at=expires_at,
            invited_by=current_user.id,
        )
        session.add(invite)

        await audit_log(
            session,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.id,
            actor_type=ActorType.ADMIN_USER,
            action="client_user.invited",
            entity_type="client_invite",
            entity_id=None,
        )

    await session.flush()

    # Send email
    tenant_name = current_user.tenant.business_name if current_user.tenant else "the platform"
    email_sender = create_email_sender()
    await _send_client_invite_email(email_sender, tenant_name, client.name, email, raw_token)

    await session.commit()

    # Re-fetch for response
    invite_obj = await invite_repo.get_by_id(session, invite.id)
    if invite_obj is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invite not found after creation",
        )
    return ClientInviteResponse(
        id=invite_obj.id,
        email=invite_obj.email,
        expires_at=invite_obj.expires_at,
        accepted_at=invite_obj.accepted_at,
        status=_derive_status(invite_obj),
    )


@tenant_router.get(
    "/clients/{client_id}/invites",
    response_model=list[ClientInviteResponse],
)
async def list_client_invites(
    client_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "clients")),
) -> list[ClientInviteResponse]:
    """List invites for a specific client."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    import uuid

    try:
        client_uid = uuid.UUID(client_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        ) from None

    # Verify client exists in this tenant (leak prevention)
    client = await client_repo.get_by_tenant_id(session, current_user.tenant_id, client_uid)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    invites = await invite_repo.get_by_client_id(session, client_uid)
    return [
        ClientInviteResponse(
            id=i.id,
            email=i.email,
            expires_at=i.expires_at,
            accepted_at=i.accepted_at,
            status=_derive_status(i),
        )
        for i in invites
    ]


@tenant_router.delete(
    "/client-invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_client_invite(
    invite_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "clients")),
) -> None:
    """Revoke (hard delete) a pending client invite."""
    import uuid

    try:
        uid = uuid.UUID(invite_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found",
        ) from None

    invite = await invite_repo.get_by_id(session, uid)
    if invite is None or invite.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found",
        )

    if invite.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot revoke an already accepted invite",
        )

    await session.delete(invite)

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="client_user.invite_revoked",
        entity_type="client_invite",
        entity_id=str(invite.id),
    )

    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Client user deactivation (tenant-scoped)
# ═══════════════════════════════════════════════════════════════════════════


@tenant_router.post(
    "/client-users/{user_id}/deactivate",
    status_code=status.HTTP_200_OK,
)
async def deactivate_client_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "clients")),
) -> dict[str, str]:
    """Deactivate a client user."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    import uuid

    try:
        target_uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client user not found",
        ) from None

    target = await client_user_repo.get_by_id(session, target_uid)
    if target is None or target.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client user not found",
        )

    if not target.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client user is already deactivated",
        )

    target.is_active = False
    await session.flush()

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="client_user.deactivated",
        entity_type="client_user",
        entity_id=str(target.id),
    )

    await session.commit()
    return {"status": "ok"}


@tenant_router.post(
    "/client-users/{user_id}/reactivate",
    status_code=status.HTTP_200_OK,
)
async def reactivate_client_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "clients")),
) -> dict[str, str]:
    """Reactivate a deactivated client user."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )

    import uuid

    try:
        target_uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client user not found",
        ) from None

    target = await client_user_repo.get_by_id(session, target_uid)
    if target is None or target.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client user not found",
        )

    if target.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client user is already active",
        )

    target.is_active = True
    await session.flush()

    await audit_log(
        session,
        tenant_id=current_user.tenant_id,
        actor_id=current_user.id,
        actor_type=ActorType.ADMIN_USER,
        action="client_user.reactivated",
        entity_type="client_user",
        entity_id=str(target.id),
    )

    await session.commit()
    return {"status": "ok"}
