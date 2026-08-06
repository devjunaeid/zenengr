"""Tenant SMTP configuration business logic (FEAT-013, TODO-139/140/141).

Owns:
- read/upsert of the per-tenant SMTP config (password stored encrypted,
  never returned)
- validation rules (port range, mode, enabled-requires-host/from_email)
- test-email sending through the resolved sender
- audit logging ("smtp_config.updated", "smtp_config.test")
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorType, SmtpSecurityMode
from app.models.tenant_smtp_config import TenantSmtpConfig
from app.services import smtp
from app.services.audit import log as audit_log

_EMAIL_ADAPTER = TypeAdapter(EmailStr)

# ── Exceptions ──────────────────────────────────────────────────────────────


class SmtpConfigNotConfiguredError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="SMTP not configured",
        )


class SmtpConfigValidationError(HTTPException):
    def __init__(self, message: str = "Invalid SMTP configuration") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=message,
        )


class SmtpConfigNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMTP config not found",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _get_row(session: AsyncSession, tenant_id: uuid.UUID) -> TenantSmtpConfig | None:
    stmt = select(TenantSmtpConfig).where(TenantSmtpConfig.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _to_response(config: TenantSmtpConfig) -> dict[str, Any]:
    """Masked response shape — never includes password/ciphertext."""
    return {
        "host": config.host,
        "port": config.port,
        "username": config.username,
        "from_email": config.from_email,
        "from_name": config.from_name,
        "mode": config.mode.value,
        "enabled": config.enabled,
        "has_password": config.password_ciphertext is not None,
    }


def _validate(config: TenantSmtpConfig) -> None:
    """Validate a (possibly partially updated) config. Raises 422 on error."""
    if config.port is not None and not 1 <= config.port <= 65535:
        raise SmtpConfigValidationError("Port must be between 1 and 65535")
    if not isinstance(config.mode, SmtpSecurityMode):
        raise SmtpConfigValidationError("Invalid SMTP security mode")
    if config.enabled and (not config.host or not config.from_email):
        raise SmtpConfigValidationError("Host and from email are required when SMTP is enabled")
    if config.from_email is not None:
        try:
            _EMAIL_ADAPTER.validate_python(config.from_email)
        except ValidationError as exc:
            raise SmtpConfigValidationError("Invalid from email address") from exc


# ── Service functions ───────────────────────────────────────────────────────


async def get_smtp_config(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Return the tenant's SMTP config (masked). Defaults when no row exists."""
    config = await _get_row(session, tenant_id)
    if config is None:
        return {
            "host": None,
            "port": None,
            "username": None,
            "from_email": None,
            "from_name": None,
            "mode": SmtpSecurityMode.STARTTLS.value,
            "enabled": False,
            "has_password": False,
        }
    return _to_response(config)


async def upsert_smtp_config(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    data: dict[str, Any],
    actor_id: uuid.UUID | None,
) -> dict[str, Any]:
    """Create-or-update the tenant's SMTP config.

    Password handling: only a non-empty password string is encrypted and
    stored; an omitted, blank ("") or None password keeps the existing
    ciphertext (has_password preserved). Setting clear_password True (or
    clearing username to None, the no-auth case) removes the stored
    ciphertext. Returns the masked response shape.
    """
    config = await _get_row(session, tenant_id)
    if config is None:
        config = TenantSmtpConfig(tenant_id=tenant_id)
        session.add(config)
        await session.flush()

    if data.get("host") is not None:
        config.host = data["host"]
    if data.get("port") is not None:
        config.port = data["port"]
    if "username" in data:
        # Normalize blank/None username to None (clearing the field).
        username = data["username"]
        config.username = username if username not in ("", None) else None
    if data.get("from_email") is not None:
        config.from_email = data["from_email"]
    if data.get("from_name") is not None:
        config.from_name = data["from_name"]
    if data.get("mode") is not None:
        config.mode = data["mode"]
    if data.get("enabled") is not None:
        config.enabled = data["enabled"]
    if "password" in data:
        # Blank/None password means "no change"; only non-empty strings
        # are treated as a new password to encrypt.
        password = data["password"]
        if password:
            config.password_ciphertext = smtp.encrypt_password(password)
    if data.get("clear_password") is True:
        config.password_ciphertext = None
    if config.username is None:
        # No-auth intent (username cleared): drop any saved password too.
        config.password_ciphertext = None

    _validate(config)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="smtp_config.updated",
        entity_type="tenant_smtp_config",
        entity_id=str(config.id),
        details={
            "host": config.host,
            "mode": config.mode.value,
            "enabled": config.enabled,
        },
    )
    await session.commit()
    return await get_smtp_config(session, tenant_id=tenant_id)


async def test_smtp_config(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    to_email: str | None,
    actor_id: uuid.UUID | None = None,
) -> None:
    """Send a test email through the tenant's SMTP config.

    Raises SmtpConfigNotConfiguredError when SMTP is missing/disabled, and
    SmtpConfigValidationError (422) when the send fails. Audits only on
    success.
    """
    config = await _get_row(session, tenant_id)
    if config is None or not config.enabled or not config.host or not config.from_email:
        raise SmtpConfigNotConfiguredError()

    password = (
        smtp.decrypt_password(config.password_ciphertext) if config.password_ciphertext else None
    )
    sender = smtp.SmtpEmailSender(
        host=config.host,
        port=config.port,
        username=config.username,
        password=password,
        mode=config.mode,
        from_email=config.from_email,
        from_name=config.from_name,
    )
    try:
        await sender.send_email(
            to=to_email or config.from_email,
            subject="ZenEngr SMTP test",
            body="This is a test email from ZenEngr. "
            "If you received it, your SMTP settings are working.",
        )
    except Exception as exc:
        raise SmtpConfigValidationError(f"Failed to send test email: {exc}") from exc

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="smtp_config.test",
        entity_type="tenant_smtp_config",
        entity_id=str(config.id),
        details={"to_email": to_email or config.from_email},
    )
    await session.commit()
