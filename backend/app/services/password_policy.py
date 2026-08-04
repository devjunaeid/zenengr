"""Tenant-configurable password policy (TODO-115)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.settings import DEFAULT_SETTINGS, get_tenant_setting_by_key


class PasswordPolicyError(HTTPException):
    """Raised when a password does not meet the tenant password policy (422)."""

    def __init__(self, min_length: int) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Password must be at least {min_length} characters",
        )


def _default_min_length() -> int:
    for entry in DEFAULT_SETTINGS:
        if entry["key"] == "password_min_length":
            return int(entry["value"])
    return 10


async def get_min_password_length(session: AsyncSession, tenant_id: uuid.UUID | None) -> int:
    """Read tenant setting password_min_length; fallback DEFAULT_SETTINGS (10).

    Super admin (tenant None) -> 10.
    """
    if tenant_id is None:
        return _default_min_length()

    setting = await get_tenant_setting_by_key(session, tenant_id, "password_min_length")
    if setting is None:
        return _default_min_length()

    try:
        return int(setting.value)
    except ValueError:
        return _default_min_length()


def validate_password_policy(password: str, min_length: int) -> None:
    """Raise PasswordPolicyError if password is shorter than min_length."""
    if len(password) < min_length:
        raise PasswordPolicyError(min_length)
