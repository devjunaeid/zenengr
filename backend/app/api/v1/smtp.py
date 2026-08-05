"""Per-tenant SMTP configuration endpoints (FEAT-013, TODO-139/140/141).

Base path: /api/v1/tenant/smtp-config
Guards: manage/tenant_settings for writes and test; all staff can read.
The password/ciphertext is never returned — only has_password.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.schemas.smtp import (
    SmtpTestRequest,
    TenantSmtpConfigResponse,
    TenantSmtpConfigUpdateRequest,
)
from app.services import tenant_smtp as smtp_service

router = APIRouter(prefix="/tenant/smtp-config", tags=["smtp"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


@router.get("/", response_model=TenantSmtpConfigResponse)
async def get_smtp_config_endpoint(
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> TenantSmtpConfigResponse:
    """Get the tenant's SMTP config (masked). All staff can read."""
    tenant_id = _get_tenant_id(user)
    data = await smtp_service.get_smtp_config(session, tenant_id=tenant_id)
    return TenantSmtpConfigResponse(**data)


@router.patch("/", response_model=TenantSmtpConfigResponse)
async def upsert_smtp_config_endpoint(
    body: TenantSmtpConfigUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "tenant_settings")),
) -> TenantSmtpConfigResponse:
    """Create or update the tenant's SMTP config. Admin only."""
    tenant_id = _get_tenant_id(user)
    data = await smtp_service.upsert_smtp_config(
        session,
        tenant_id=tenant_id,
        data=body.model_dump(),
        actor_id=user.id,
    )
    return TenantSmtpConfigResponse(**data)


@router.post("/test")
async def test_smtp_config_endpoint(
    body: SmtpTestRequest | None = None,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "tenant_settings")),
) -> dict[str, str | bool]:
    """Send a test email through the configured SMTP server. Admin only."""
    tenant_id = _get_tenant_id(user)
    await smtp_service.test_smtp_config(
        session,
        tenant_id=tenant_id,
        to_email=body.to_email if body is not None else None,
        actor_id=user.id,
    )
    return {"ok": True, "message": "Test email sent"}
