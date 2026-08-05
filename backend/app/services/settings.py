"""Default tenant settings, permission levels, and runtime management.

Each entry: key name, default value, permission level.

Validation rules per setting key:
- currency: ISO 4217 alpha-3
- timezone: IANA timezone name via zoneinfo
- invoice_number_format: must contain {seq} token
- date_format: allowlist
- password_min_length: integer between 8 and 64
"""

from __future__ import annotations

import uuid
import zoneinfo
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AdminUserRole, PermissionLevel
from app.models.tenant_setting import TenantSetting

# ── Default settings ────────────────────────────────────────────────────────

DEFAULT_SETTINGS: list[dict[str, Any]] = [
    {
        "key": "currency",
        "value": "USD",
        "permission_level": PermissionLevel.TENANT_ADMIN_EDITABLE,
    },
    {
        "key": "invoice_number_format",
        "value": "INV-{YYYY}-{SEQ:04d}",
        "permission_level": PermissionLevel.TENANT_ADMIN_EDITABLE,
    },
    {
        "key": "timezone",
        "value": "UTC",
        "permission_level": PermissionLevel.TENANT_ADMIN_EDITABLE,
    },
    {
        "key": "date_format",
        "value": "YYYY-MM-DD",
        "permission_level": PermissionLevel.TENANT_ADMIN_EDITABLE,
    },
    {
        "key": "email_sender_identity",
        "value": "noreply@zenengr.com",
        "permission_level": PermissionLevel.TENANT_ADMIN_VIEWABLE,
    },
    {
        "key": "password_min_length",
        "value": "10",
        "permission_level": PermissionLevel.TENANT_ADMIN_EDITABLE,
    },
]

# ── Validation ──────────────────────────────────────────────────────────────

_VALID_DATE_FORMATS = frozenset({"YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"})


def validate_setting_value(key: str, value: str) -> None:
    """Validate setting value by key. Raises 422 on invalid."""
    if key == "currency":
        if not _is_valid_currency(value):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid currency '{value}'. Must be ISO 4217 alpha-3 code (e.g. USD, EUR)."
                ),
            )
    elif key == "timezone":
        try:
            zoneinfo.ZoneInfo(value)
        except ValueError, TypeError, zoneinfo.ZoneInfoNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid timezone '{value}'. "
                    "Must be IANA timezone name (e.g. UTC, America/New_York)."
                ),
            ) from None
    elif key == "invoice_number_format" and "{seq}" not in value.lower():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(f"Invalid invoice_number_format '{value}'. Must contain '{{seq}}' token."),
        )
    elif key == "date_format" and value not in _VALID_DATE_FORMATS:
        allowed = ", ".join(sorted(_VALID_DATE_FORMATS))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid date_format '{value}'. Allowed: {allowed}.",
        )
    elif key == "password_min_length":
        try:
            parsed = int(value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="password_min_length must be an integer between 8 and 64",
            ) from None
        if not 8 <= parsed <= 64:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="password_min_length must be an integer between 8 and 64",
            )


def _is_valid_currency(code: str) -> bool:
    """Basic ISO 4217 alpha-3 check (3 uppercase letters)."""
    return len(code) == 3 and code.isalpha() and code.isupper()


# ── Permission helpers ──────────────────────────────────────────────────────


def can_edit_setting(permission_level: PermissionLevel, role: AdminUserRole) -> bool:
    """Check if role can edit a setting with given permission level.

    Super admin can edit everything.
    Tenant admin can edit tenant_admin_editable only.
    Others cannot edit any settings.
    """
    if role == AdminUserRole.SUPER_ADMIN:
        return True
    if role != AdminUserRole.ADMIN:
        return False
    return permission_level == PermissionLevel.TENANT_ADMIN_EDITABLE


def should_mask_value(permission_level: PermissionLevel, role: AdminUserRole) -> bool:
    """Return True if value should be masked (null) for the caller."""
    # Super admin sees everything unmasked
    if role == AdminUserRole.SUPER_ADMIN:
        return False
    # Tenant callers see super_admin_only values as null
    return permission_level == PermissionLevel.SUPER_ADMIN_ONLY


# ── Service functions ───────────────────────────────────────────────────────


async def get_tenant_settings(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    role: AdminUserRole,
) -> list[dict[str, Any]]:
    """Get all settings for a tenant with editable flag and masking.

    Returns every DEFAULT_SETTINGS entry merged with stored overrides:
    value is the stored row value when present, else the default. Extra
    stored rows (e.g. super_admin_only) are appended after the defaults.

    Masking: super_admin_only values shown as null for tenant callers.
    """
    result = await session.execute(
        select(TenantSetting).where(TenantSetting.tenant_id == tenant_id)
    )
    settings = result.scalars().all()

    stored = {s.key: s for s in settings}
    default_keys = {d["key"] for d in DEFAULT_SETTINGS}

    items: list[dict[str, Any]] = []
    for default in DEFAULT_SETTINGS:
        key = default["key"]
        setting = stored.get(key)
        if setting is not None:
            value: str | None = setting.value
            permission_level = setting.permission_level
        else:
            value = default["value"]
            permission_level = default["permission_level"]

        if should_mask_value(permission_level, role):
            value = None

        items.append(
            {
                "key": key,
                "value": value,
                "permission_level": permission_level.value,
                "editable": can_edit_setting(permission_level, role),
            }
        )

    # Stored rows not covered by DEFAULT_SETTINGS (e.g. super_admin_only)
    for s in settings:
        if s.key in default_keys:
            continue
        extra_value: str | None = s.value
        if should_mask_value(s.permission_level, role):
            extra_value = None

        items.append(
            {
                "key": s.key,
                "value": extra_value,
                "permission_level": s.permission_level.value,
                "editable": can_edit_setting(s.permission_level, role),
            }
        )

    return items


async def get_tenant_setting_by_key(
    session: AsyncSession, tenant_id: uuid.UUID, key: str
) -> TenantSetting | None:
    """Fetch a single setting by key for a tenant."""
    result = await session.execute(
        select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id,
            TenantSetting.key == key,
        )
    )
    return result.scalar_one_or_none()


async def update_tenant_setting(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    key: str,
    value: str,
) -> dict[str, Any]:
    """Update a tenant setting, creating the row on first write (upsert).

    Validates the value with validate_setting_value. Unknown keys (no stored
    row and no DEFAULT_SETTINGS entry) raise 404; invalid values raise 422.
    Returns {key, old_value, new_value} (old_value None when creating).
    """
    setting = await get_tenant_setting_by_key(session, tenant_id, key)
    if setting is None:
        default = next((d for d in DEFAULT_SETTINGS if d["key"] == key), None)
        if default is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found",
            )

        validate_setting_value(key, value)
        setting = TenantSetting(
            tenant_id=tenant_id,
            key=key,
            value=value,
            permission_level=default["permission_level"],
        )
        session.add(setting)
        await session.flush()
        await session.refresh(setting)
        await session.commit()
        return {"key": key, "old_value": None, "new_value": setting.value}

    # Validate
    validate_setting_value(key, value)

    old_value = setting.value
    setting.value = value
    await session.flush()
    await session.refresh(setting)
    await session.commit()

    return {"key": key, "old_value": old_value, "new_value": setting.value}
