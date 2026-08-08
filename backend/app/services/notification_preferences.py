"""Per-user notification preferences (TODO-116/117).

Default behaviour: every event type is enabled. A user opts out per event
type; missing rows mean "enabled" (default).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationEventType
from app.models.notification_preference import NotificationPreference

_USER_TYPES = ("admin_user", "client_user")


async def list_preferences(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
    tenant_id: uuid.UUID | None,
    channel: NotificationChannel,
) -> list[dict[str, Any]]:
    """Get-or-create a preference row per event type for a channel; return enabled map list.

    Order: new_comment, invoice_issued, payment_received, milestone_completed,
    refund_recorded, advance_applied, project_created.
    """
    if user_type not in _USER_TYPES:
        raise ValueError(f"Unknown user_type: {user_type}")

    result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.user_type == user_type,
            NotificationPreference.channel == channel,
        )
    )
    existing = {row.event_type: row for row in result.scalars().all()}

    rows: list[dict[str, Any]] = []
    created = False
    for event_type in NotificationEventType:
        row = existing.get(event_type)
        if row is None:
            row = NotificationPreference(
                user_id=user_id,
                user_type=user_type,
                tenant_id=tenant_id,
                event_type=event_type,
                channel=channel,
                enabled=True,
            )
            session.add(row)
            await session.flush()
            created = True
        rows.append({"event_type": event_type.value, "enabled": bool(row.enabled)})
    if created:
        await session.commit()
    return rows


async def update_preferences(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
    tenant_id: uuid.UUID | None,
    channel: NotificationChannel,
    entries: list[tuple[NotificationEventType, bool]],
) -> list[dict[str, Any]]:
    """Upsert preferences for the given entries on a channel; commit; return full list."""
    if user_type not in _USER_TYPES:
        raise ValueError(f"Unknown user_type: {user_type}")

    result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.user_type == user_type,
            NotificationPreference.channel == channel,
        )
    )
    existing = {row.event_type: row for row in result.scalars().all()}

    for event_type, enabled in entries:
        row = existing.get(event_type)
        if row is None:
            row = NotificationPreference(
                user_id=user_id,
                user_type=user_type,
                tenant_id=tenant_id,
                event_type=event_type,
                channel=channel,
                enabled=enabled,
            )
            session.add(row)
        else:
            row.enabled = enabled

    await session.commit()
    return await list_preferences(
        session,
        user_id=user_id,
        user_type=user_type,
        tenant_id=tenant_id,
        channel=channel,
    )


async def get_enabled_map(
    session: AsyncSession,
    *,
    user_type: str,
    user_ids: list[uuid.UUID],
    event_type: NotificationEventType,
    channel: NotificationChannel,
) -> dict[uuid.UUID, bool]:
    """Batch-select enabled prefs for users + event + channel; missing = default enabled.

    Returns {user_id: enabled} for every requested user_id.
    """
    if not user_ids:
        return {}

    result = await session.execute(
        select(NotificationPreference).where(
            NotificationPreference.user_type == user_type,
            NotificationPreference.user_id.in_(user_ids),
            NotificationPreference.event_type == event_type,
            NotificationPreference.channel == channel,
        )
    )
    prefs = {row.user_id: bool(row.enabled) for row in result.scalars().all()}
    return {user_id: prefs.get(user_id, True) for user_id in user_ids}
