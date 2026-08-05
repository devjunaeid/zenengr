"""Invite endpoints: tenant (admin) and public (registration)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import require_permission
from app.core.security import create_access_token, hash_password
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import ActorType, AdminUserRole
from app.models.invite import Invite
from app.repositories import invites as invite_repo
from app.schemas.auth import LoginResponse, UserResponse
from app.schemas.invites import (
    InviteCreateRequest,
    InviteLookupResponse,
    InviteResponse,
    RegisterRequest,
)
from app.services.audit import log as audit_log
from app.services.smtp import send_tenant_email

# ── Tenant-scoped (admin: manage admin_users) ──────────────────────────────

tenant_router = APIRouter(prefix="/tenant", tags=["invites"])

# ── Public (no auth required) ──────────────────────────────────────────────

public_router = APIRouter(prefix="/auth", tags=["auth"])


# ── Helpers ────────────────────────────────────────────────────────────────


def _hash_token(raw: str) -> str:
    """SHA-256 hex digest of raw token."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _derive_status(invite: Invite) -> str:
    if invite.accepted_at is not None:
        return "accepted"
    if invite.expires_at < datetime.now(UTC):
        return "expired"
    return "pending"


async def _send_invite_email(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant_name: str,
    email: str,
    raw_token: str,
) -> None:
    """Send invitation email with accept link."""
    settings = get_settings()
    accept_url = f"{settings.admin_portal_base_url}/accept-invite?token={raw_token}"
    subject = f"You're invited to join {tenant_name}"
    body = (
        f"You've been invited to join {tenant_name}.\n\n"
        f"Click the link below to accept the invitation and set up your account:\n\n"
        f"{accept_url}\n\n"
        f"This link expires in {settings.invite_ttl_hours} hours."
    )
    await send_tenant_email(session, tenant_id=tenant_id, to=email, subject=subject, body=body)


# ── Tenant endpoints ───────────────────────────────────────────────────────


@tenant_router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> InviteResponse:
    """Create invite for admin user. Resends if pending/expired invite exists."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    settings = get_settings()
    email = body.email.lower().strip()

    # Check existing admin user in this tenant
    from app.repositories import admin_users as admin_user_repo

    existing = await admin_user_repo.get_by_email(session, email)
    if existing is not None and existing.tenant_id == current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin user with this email already exists in this tenant",
        )

    # Check admin_users limit before creating new invite
    from app.services.limits import LimitExceededError, check_limit

    try:
        await check_limit(session, current_user.tenant_id, "admin_users", increment=1)
    except LimitExceededError:
        raise  # Re-raise the 403

    # Find existing invite for this email + tenant
    existing_invite = await invite_repo.get_any_by_email_and_tenant(
        session, email, current_user.tenant_id
    )

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.invite_ttl_hours)

    if existing_invite is not None:
        # Regenerate token + reset expiry (resend path)
        existing_invite.token = token_hash
        existing_invite.expires_at = expires_at
        existing_invite.accepted_at = None
        invite = existing_invite

        await audit_log(
            session,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.id,
            actor_type=ActorType.ADMIN_USER,
            action="invite.resent",
            entity_type="invite",
            entity_id=str(invite.id),
        )
    else:
        invite = Invite(
            tenant_id=current_user.tenant_id,
            email=email,
            role=body.role,
            token=token_hash,
            expires_at=expires_at,
            invited_by=current_user.id,
        )
        session.add(invite)

        await audit_log(
            session,
            tenant_id=current_user.tenant_id,
            actor_id=current_user.id,
            actor_type=ActorType.ADMIN_USER,
            action="invite.created",
            entity_type="invite",
            entity_id=None,  # ID not yet generated by DB
        )

    await session.flush()

    # Send email
    from app.repositories.admin_users import get_by_id

    inviter = await get_by_id(session, current_user.id)
    tenant_name = inviter.tenant.business_name if inviter and inviter.tenant else "the platform"
    await _send_invite_email(
        session,
        tenant_id=current_user.tenant_id,
        tenant_name=tenant_name,
        email=email,
        raw_token=raw_token,
    )

    await session.commit()

    # Build response
    invite_obj = await invite_repo.get_by_id(session, invite.id)
    if invite_obj is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invite not found after creation",
        )
    return InviteResponse(
        id=invite_obj.id,
        email=invite_obj.email,
        role=invite_obj.role,
        expires_at=invite_obj.expires_at,
        accepted_at=invite_obj.accepted_at,
        status=_derive_status(invite_obj),
    )


@tenant_router.get("/invites", response_model=list[InviteResponse])
async def list_invites(
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> list[InviteResponse]:
    """List invites for current tenant, newest first."""
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    invites = await invite_repo.get_by_tenant_id(
        session, current_user.tenant_id, page=page, page_size=page_size
    )
    return [
        InviteResponse(
            id=i.id,
            email=i.email,
            role=i.role,
            expires_at=i.expires_at,
            accepted_at=i.accepted_at,
            status=_derive_status(i),
        )
        for i in invites
    ]


@tenant_router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AdminUser = Depends(require_permission("manage", "admin_users")),
) -> None:
    """Revoke (hard delete) a pending invite."""
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
        action="invite.revoked",
        entity_type="invite",
        entity_id=str(invite.id),
    )

    await session.commit()


# ── Public endpoints ───────────────────────────────────────────────────────


@public_router.get("/invite/{token}", response_model=InviteLookupResponse)
async def lookup_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
) -> InviteLookupResponse:
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

    return InviteLookupResponse(
        email=invite.email,
        role=invite.role,
        tenant_name=invite.tenant.business_name,
        expires_at=invite.expires_at,
    )


@public_router.post("/register", response_model=LoginResponse)
async def register_from_invite(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    """Register admin user from valid invite. Returns auto-login JWT."""
    # Password policy
    if len(body.password) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be at least 10 characters",
        )

    token_hash = _hash_token(body.token)
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

    # Create admin user
    new_user = AdminUser(
        tenant_id=invite.tenant_id,
        email=invite.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=AdminUserRole(invite.role.value),
        is_active=True,
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
        actor_type=ActorType.ADMIN_USER,
        action="user.registered",
        entity_type="admin_user",
        entity_id=str(new_user.id),
        details={"invite_id": str(invite.id), "invited_by": str(invite.invited_by)},
    )

    await session.commit()
    await session.refresh(new_user)

    # Auto-login: issue JWT
    token = create_access_token(
        user_id=str(new_user.id),
        tenant_id=str(new_user.tenant_id) if new_user.tenant_id else None,
        role=new_user.role.value,
        realm="admin",
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106
        user=UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role.value,
            tenant_id=str(new_user.tenant_id) if new_user.tenant_id else None,
        ),
    )
