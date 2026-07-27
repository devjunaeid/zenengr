"""Auth endpoints: login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.services.auth import (
    AccountDeactivatedError,
    AuthenticationError,
    TenantCancelledError,
    TenantSuspendedError,
    authenticate_admin,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            tenant_id=str(user.tenant_id) if user.tenant_id else None,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def me(
    user: AdminUser = Depends(get_current_admin_user),
) -> UserResponse:
    """Return authenticated user profile."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
    )
