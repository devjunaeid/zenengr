"""Auth endpoints: login, me, self-service profile/password/activity (FEAT-011)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import NotificationChannel
from app.schemas.account import (
    ActivityResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    NotificationPreferenceResponse,
    NotificationPreferencesUpdateRequest,
    ProfileUpdateRequest,
    VerifyEmailRequest,
)
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.services.account import (
    change_password,
    forgot_password_admin,
    list_activity,
    update_admin_profile,
    verify_email_admin,
)
from app.services.auth import (
    AccountDeactivatedError,
    AuthenticationError,
    TenantCancelledError,
    TenantSuspendedError,
    authenticate_admin,
)
from app.services.notification_preferences import list_preferences, update_preferences
from app.services.password_policy import get_min_password_length
from app.services.roles import effective_permissions

router = APIRouter(prefix="/auth", tags=["auth"])


async def _to_user_response(session: AsyncSession, user: AdminUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        role_id=user.role_id,
        permissions=await effective_permissions(session, user=user),
        avatar_url=user.avatar_url,
        phone=user.phone,
        timezone=user.timezone,
        language=user.language,
        pending_email=user.pending_email,
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    """Authenticate admin user, return JWT + user profile."""
    try:
        token, token_type, user = await authenticate_admin(session, body.email, body.password)
    except TenantSuspendedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except TenantCancelledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (AuthenticationError, AccountDeactivatedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    return LoginResponse(
        access_token=token,
        token_type=token_type,
        user=await _to_user_response(session, user),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    user: AdminUser = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Return authenticated user profile."""
    return await _to_user_response(session, user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user: AdminUser = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    """Self-service: update own profile fields (avatar, phone, timezone, language)."""
    updated = await update_admin_profile(
        session,
        user=user,
        full_name=body.full_name,
        avatar_url=body.avatar_url,
        phone=body.phone,
        timezone=body.timezone,
        language=body.language,
        email=body.email,
    )
    return await _to_user_response(session, updated)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password_endpoint(
    body: ChangePasswordRequest,
    user: AdminUser = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Self-service: change own password (tenant password policy applies)."""
    min_length = await get_min_password_length(session, user.tenant_id)
    await change_password(
        session,
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
        min_length=min_length,
    )
    return {"status": "ok"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Public: request password reset email. Always 200 (no existence leak)."""
    await forgot_password_admin(session, email=body.email)
    return {"status": "ok"}


@router.get("/notification-preferences", response_model=list[NotificationPreferenceResponse])
async def notification_preferences(
    user: AdminUser = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
    channel: NotificationChannel = Query(default=NotificationChannel.EMAIL),
) -> list[NotificationPreferenceResponse]:
    """Return the caller's per-event notification preferences for a channel (TODO-116)."""
    prefs = await list_preferences(
        session,
        user_id=user.id,
        user_type="admin_user",
        tenant_id=user.tenant_id,
        channel=channel,
    )
    return [NotificationPreferenceResponse(**p) for p in prefs]


@router.patch("/notification-preferences", response_model=list[NotificationPreferenceResponse])
async def update_notification_preferences(
    body: NotificationPreferencesUpdateRequest,
    user: AdminUser = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationPreferenceResponse]:
    """Upsert the caller's per-event notification preferences for a channel (TODO-116)."""
    entries = [(e.event_type, e.enabled) for e in body.preferences]
    prefs = await update_preferences(
        session,
        user_id=user.id,
        user_type="admin_user",
        tenant_id=user.tenant_id,
        channel=body.channel,
        entries=entries,
    )
    return [NotificationPreferenceResponse(**p) for p in prefs]


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    body: VerifyEmailRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Public: confirm pending email change with single-use token (TODO-110)."""
    await verify_email_admin(session, token=body.token)
    return {"status": "ok"}


@router.get("/activity", response_model=list[ActivityResponse])
async def activity(
    user: AdminUser = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[ActivityResponse]:
    """Return the caller's activity history, newest first (TODO-119)."""
    entries = await list_activity(session, user_id=user.id)
    return [
        ActivityResponse(
            id=e.id,
            event_type=e.event_type,
            description=e.description,
            old_value=e.old_value,
            new_value=e.new_value,
            created_at=e.created_at,
        )
        for e in entries
    ]
