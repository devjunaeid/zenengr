"""Append-only audit log service.

Usage:
    await log(session, tenant_id=..., actor_id=..., actor_type=...,
              action="invite.created", entity_type="invite", entity_id=str(invite.id))
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import ActorType


async def log(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    actor_type: ActorType,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write an append-only audit log entry."""
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )
    session.add(entry)
