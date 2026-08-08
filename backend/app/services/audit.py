"""Append-only audit log service.

Usage:
    await log(session, tenant_id=..., actor_id=..., actor_type=...,
              action="invite.created", entity_type="invite", entity_id=str(invite.id))
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_invite import ClientInvite
from app.models.client_user import ClientUser
from app.models.enums import ActorType
from app.models.file_asset import FileAsset
from app.models.file_folder import FileFolder
from app.models.invite import Invite
from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.project import Project
from app.models.service import Service
from app.models.tenant import Tenant


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


async def list_audit_logs(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    page: int = 1,
    page_size: int = 20,
    action: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict[str, Any]:
    """Paginated audit log query with optional filters.

    tenant_id=None selects platform-scope entries (tenant_id IS NULL);
    a tenant id selects that tenant's entries. action filters by prefix;
    from_date/to_date filter created_at (ISO-8601 date or datetime).
    Returns {"items": [AuditLog, ...], "total", "page", "page_size"}.
    """
    query = select(AuditLog)
    if tenant_id is not None:
        query = query.where(AuditLog.tenant_id == tenant_id)
    else:
        query = query.where(AuditLog.tenant_id.is_(None))

    if action:
        query = query.where(AuditLog.action.startswith(action))
    if from_date:
        query = query.where(AuditLog.created_at >= _parse_filter_date(from_date))
    if to_date:
        query = query.where(AuditLog.created_at <= _parse_filter_date(to_date))

    count_q = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)
    result = await session.execute(query)
    entries = list(result.scalars().all())

    return {"items": entries, "total": total, "page": page, "page_size": page_size}


async def audit_names(
    session: AsyncSession,
    *,
    entries: list[AuditLog],
) -> dict[str, dict[str, str | None]]:
    """Resolve actor + entity display names for audit entries.

    Returns {str(entry.id): {"actor_name": ..., "entity_label": ...}}.
    Unresolvable names (deleted rows, unknown entity types, malformed ids)
    come back as None; the frontend falls back to a humanized entity type
    and truncated id.
    """
    result: dict[str, dict[str, str | None]] = {
        str(e.id): {"actor_name": None, "entity_label": None} for e in entries
    }

    # ── Actors ────────────────────────────────────────────────────────────
    admin_ids = {
        e.actor_id
        for e in entries
        if e.actor_type == ActorType.ADMIN_USER and e.actor_id is not None
    }
    if admin_ids:
        rows = (
            await session.execute(
                select(AdminUser).where(AdminUser.id.in_(admin_ids))
            )
        ).scalars()
        by_id = {str(u.id): u.full_name for u in rows}
        for e in entries:
            if (
                e.actor_type == ActorType.ADMIN_USER
                and e.actor_id is not None
                and str(e.actor_id) in by_id
            ):
                result[str(e.id)]["actor_name"] = by_id[str(e.actor_id)]

    client_ids = {
        e.actor_id
        for e in entries
        if e.actor_type == ActorType.CLIENT_USER and e.actor_id is not None
    }
    if client_ids:
        client_rows = (
            await session.execute(
                select(ClientUser).where(ClientUser.id.in_(client_ids))
            )
        ).scalars()
        by_id = {str(u.id): u.full_name for u in client_rows}
        for e in entries:
            if (
                e.actor_type == ActorType.CLIENT_USER
                and e.actor_id is not None
                and str(e.actor_id) in by_id
            ):
                result[str(e.id)]["actor_name"] = by_id[str(e.actor_id)]

    for e in entries:
        if e.actor_type == ActorType.SYSTEM:
            result[str(e.id)]["actor_name"] = "System"
        elif e.actor_type == ActorType.SUPER_ADMIN:
            result[str(e.id)]["actor_name"] = "Super admin"

    # ── Entities ──────────────────────────────────────────────────────────
    groups: dict[tuple[str, str], list[AuditLog]] = {}
    for e in entries:
        if e.entity_type and e.entity_id:
            groups.setdefault((e.entity_type, e.entity_id), []).append(e)

    for (entity_type, entity_id), group in groups.items():
        label = await _entity_label(session, entity_type, entity_id)
        if label is None:
            continue
        for e in group:
            result[str(e.id)]["entity_label"] = label

    return result


# Static labels for entity types without a DB row lookup.
_STATIC_ENTITY_LABELS: dict[str, str] = {
    "comment": "Comment",
    "smtp": "SMTP config",
}

# entity_type -> (model, label attribute) for row lookups.
_ENTITY_MODEL_LOOKUPS: dict[str, tuple[Any, str]] = {
    "project": (Project, "name"),
    "client": (Client, "name"),
    "service": (Service, "name"),
    "admin_user": (AdminUser, "full_name"),
    "client_user": (ClientUser, "full_name"),
    "invite": (Invite, "email"),
    "client_invite": (ClientInvite, "email"),
    "plan": (Plan, "name"),
    "file": (FileAsset, "name"),
    "file_asset": (FileAsset, "name"),
    "folder": (FileFolder, "name"),
    "tenant": (Tenant, "business_name"),
}


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def _parse_filter_date(value: str) -> datetime:
    """Parse ISO-8601 date/datetime into a timezone-aware datetime."""
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid date") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


async def _entity_label(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> str | None:
    """Resolve a single entity's display label, or None if unresolvable."""
    if entity_type in _STATIC_ENTITY_LABELS:
        return _STATIC_ENTITY_LABELS[entity_type]

    # Invoice labels from invoice_number, falling back to a static label.
    if entity_type == "invoice":
        uid = _parse_uuid(entity_id)
        if uid is None:
            return None
        row = (
            await session.execute(select(Invoice).where(Invoice.id == uid))
        ).scalar_one_or_none()
        if row is None:
            return None
        return row.invoice_number or "Invoice"

    lookup = _ENTITY_MODEL_LOOKUPS.get(entity_type)
    if lookup is None:
        return None
    model, attr = lookup
    uid = _parse_uuid(entity_id)
    if uid is None:
        return None
    row = (
        await session.execute(select(model).where(model.id == uid))
    ).scalar_one_or_none()
    if row is None:
        return None
    return str(getattr(row, attr))
