"""Notification dispatch (FEAT-010, TODO-107; FEAT-017, TODO-170/172).

TODO-108/TODO-116: recipients are filtered by their per-user
NotificationPreference for the event type (missing = default enabled).
Email failures are swallowed so a notification problem never breaks the
primary action (comment post).

FEAT-017 (TODO-170/172): in-app notification rows plus a WebSocket fan-out.
- notify_users / create_notification_row persist Notification rows.
- staff_keys_with_permission resolves staff recipients by effective
  permission for the event's module (FEAT-016 grants; super_admin/tenant-
  admin bypass via role_has_permission; a "view" action is also satisfied
  by a "manage" grant on the same resource, since manage implies read
  access in the FR-4.2 matrix).
- client_keys_for_client mirrors events to a client's active users.
- filter_keys_by_pref applies the in-app channel preference (missing rows
  default to enabled).
- notify_* emitters are the per-event convenience entry points; business
  services call them after their own commit (TODO-173). Emitters take ids,
  fetch fresh rows via the session, and never raise into the caller
  (services wrap them with safe_notify).
"""

from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.admin_user import AdminUser
from app.models.client_user import ClientUser
from app.models.comment import Comment
from app.models.enums import (
    NotificationChannel,
    NotificationEventType,
)
from app.models.invoice import Invoice
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
from app.models.transaction import Transaction
from app.services.notification_preferences import get_enabled_map
from app.services.permissions import has_permission, role_has_permission
from app.services.smtp import send_tenant_email
from app.services.ws import manager

logger = logging.getLogger(__name__)

_USER_TYPE_ADMIN = "admin_user"
_USER_TYPE_CLIENT = "client_user"


async def dispatch_new_comment(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    comment: Comment,
    excludes_user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> None:
    """Notify active tenant staff and the project's client users by email.

    The actor (excludes_user_id) is skipped. Admin recipients get the
    admin portal link; client recipients get the client portal link.
    Recipients are filtered by their NEW_COMMENT notification preference
    (missing preference rows default to enabled).
    """
    try:
        project = (
            await session.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if project is None:
            return

        settings = get_settings()
        recipients: list[tuple[str, str]] = []

        admin_stmt = select(AdminUser).where(
            AdminUser.tenant_id == tenant_id,
            AdminUser.is_active.is_(True),
        )
        admins = (await session.execute(admin_stmt)).scalars().all()
        admin_ids = [admin.id for admin in admins if admin.id != excludes_user_id]
        admin_enabled = await get_enabled_map(
            session,
            user_type=_USER_TYPE_ADMIN,
            user_ids=admin_ids,
            event_type=NotificationEventType.NEW_COMMENT,
            channel=NotificationChannel.EMAIL,
        )
        for admin in admins:
            if admin.id == excludes_user_id:
                continue
            if not admin_enabled.get(admin.id, True):
                continue
            recipients.append((admin.email, settings.admin_portal_base_url))

        client_stmt = select(ClientUser).where(
            ClientUser.client_id == project.client_id,
            ClientUser.is_active.is_(True),
        )
        client_users = (await session.execute(client_stmt)).scalars().all()
        client_ids = [cu.id for cu in client_users if cu.id != excludes_user_id]
        client_enabled = await get_enabled_map(
            session,
            user_type=_USER_TYPE_CLIENT,
            user_ids=client_ids,
            event_type=NotificationEventType.NEW_COMMENT,
            channel=NotificationChannel.EMAIL,
        )
        for client_user in client_users:
            if client_user.id == excludes_user_id:
                continue
            if not client_enabled.get(client_user.id, True):
                continue
            recipients.append((client_user.email, settings.client_portal_base_url))

        for email, portal_base_url in recipients:
            await send_tenant_email(
                session,
                tenant_id=tenant_id,
                to=email,
                subject=f"[{project.name}] New comment from {comment.author_name}",
                body=(
                    f"{comment.author_name} commented on {project.name}:\n\n"
                    f"{comment.content[:200]}\n\n"
                    f"View the project: {portal_base_url}/projects/{project_id}"
                ),
            )
    except Exception:
        logger.exception("Comment notification failed")


# ── Row creation + fan-out ───────────────────────────────────────────────


async def create_notification_row(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID,
    user_type: str,
    event_type: NotificationEventType,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    data: dict[str, Any] | None = None,
) -> Notification:
    """Persist a single Notification row (flush only; caller commits)."""
    row = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        user_type=user_type,
        event_type=event_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        data=data or {},
    )
    session.add(row)
    await session.flush()
    return row


def _notification_payload(row: Notification) -> dict[str, Any]:
    """WS payload for a persisted notification row."""
    return {
        "id": str(row.id),
        "event_type": row.event_type.value,
        "title": row.title,
        "body": row.body,
        "entity_type": row.entity_type,
        "entity_id": row.entity_id,
        "data": row.data or {},
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


async def notify_users(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    event_type: NotificationEventType,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    data: dict[str, Any] | None = None,
    recipient_keys: list[str],
    push_after: bool = True,
) -> list[Notification]:
    """Create one Notification row per recipient key; commit; push over WS.

    A recipient key is `"<user_type>:<user_id>"`. Malformed keys are
    skipped. Each recipient receives the payload for its own row.
    """
    deliveries: list[tuple[str, Notification]] = []
    for key in recipient_keys:
        parts = key.split(":", 1)
        if len(parts) != 2:
            continue
        user_type, user_id_str = parts
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            continue
        row = await create_notification_row(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            user_type=user_type,
            event_type=event_type,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            data=data,
        )
        deliveries.append((key, row))
    await session.commit()
    if push_after:
        for key, row in deliveries:
            await manager.broadcast_to_keys([key], _notification_payload(row))
    return [row for _, row in deliveries]


# ── Recipient resolution ──────────────────────────────────────────────────


async def staff_keys_with_permission(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    action: str,
    resource: str,
) -> list[str]:
    """Keys of active tenant staff who may see the event's module.

    DB-backed roles go through role_has_permission (super_admin/tenant-admin
    names bypass); legacy users (role_id NULL or missing role row) fall back
    to the static matrix via has_permission — same resolution as
    dependencies.require_permission. A "view" action is additionally
    satisfied by a "manage" grant on the same resource (manage implies read
    access in the FR-4.2 matrix).
    """
    stmt = (
        select(AdminUser)
        .where(AdminUser.tenant_id == tenant_id, AdminUser.is_active.is_(True))
        .options(selectinload(AdminUser.role_ref))
    )
    users = (await session.execute(stmt)).scalars().all()
    keys: list[str] = []
    for user in users:
        role = user.role_ref
        if role is None:
            granted = has_permission(user.role, action, resource)
            if not granted and action == "view":
                granted = has_permission(user.role, "manage", resource)
        else:
            granted = await role_has_permission(
                session, role=role, action=action, resource=resource
            )
            if not granted and action == "view":
                granted = await role_has_permission(
                    session, role=role, action="manage", resource=resource
                )
        if granted:
            keys.append(f"{_USER_TYPE_ADMIN}:{user.id}")
    return keys


async def client_keys_for_client(session: AsyncSession, *, client_id: uuid.UUID) -> list[str]:
    """Keys of active client users belonging to the given client."""
    stmt = select(ClientUser).where(
        ClientUser.client_id == client_id,
        ClientUser.is_active.is_(True),
    )
    users = (await session.execute(stmt)).scalars().all()
    return [f"{_USER_TYPE_CLIENT}:{user.id}" for user in users]


async def filter_keys_by_pref(
    session: AsyncSession,
    *,
    event_type: NotificationEventType,
    keys: list[str],
) -> list[str]:
    """Keep only keys whose user has the event enabled for the in-app channel.

    Keys are grouped by user_type for a batched preference lookup; missing
    preference rows default to enabled.
    """
    grouped: dict[str, list[uuid.UUID]] = {_USER_TYPE_ADMIN: [], _USER_TYPE_CLIENT: []}
    valid_keys: list[str] = []
    for key in keys:
        parts = key.split(":", 1)
        if len(parts) != 2 or parts[0] not in grouped:
            continue
        try:
            user_id = uuid.UUID(parts[1])
        except ValueError:
            continue
        grouped[parts[0]].append(user_id)
        valid_keys.append(key)

    enabled_ids: set[uuid.UUID] = set()
    for user_type, user_ids in grouped.items():
        if not user_ids:
            continue
        enabled = await get_enabled_map(
            session,
            user_type=user_type,
            user_ids=user_ids,
            event_type=event_type,
            channel=NotificationChannel.INAPP,
        )
        enabled_ids.update(uid for uid, on in enabled.items() if on)

    return [key for key in valid_keys if uuid.UUID(key.split(":", 1)[1]) in enabled_ids]


# ── Convenience emitters ──────────────────────────────────────────────────


async def safe_notify(coro: Any) -> None:
    """Await a notification emitter, logging + swallowing any failure.

    Mirrors the send_tenant_email philosophy: a notification problem must
    never break the wrapped business action (the emitter's own commit via
    notify_users can fail).
    """
    try:
        await coro
    except Exception:
        logger.exception("In-app notification dispatch failed")


async def notify_comment_created(
    session: AsyncSession,
    *,
    comment_id: uuid.UUID,
) -> None:
    """In-app NEW_COMMENT push for staff (post/comments) + the project's
    client users (shared comments only). The author's own key is skipped
    (author type derived from the comment row)."""
    comment = await session.get(Comment, comment_id)
    if comment is None:
        return
    project = await session.get(Project, comment.project_id)
    if project is None:
        return

    keys = await staff_keys_with_permission(
        session,
        tenant_id=project.tenant_id,
        action="post",
        resource="comments",
    )
    if not comment.is_internal:
        keys.extend(await client_keys_for_client(session, client_id=project.client_id))

    actor_type = (
        _USER_TYPE_ADMIN if comment.author_type.value.startswith("tenant_") else _USER_TYPE_CLIENT
    )
    actor_key = f"{actor_type}:{comment.author_id}"
    keys = [key for key in keys if key != actor_key]

    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.NEW_COMMENT, keys=keys
    )
    if not keys:
        return
    await notify_users(
        session,
        tenant_id=project.tenant_id,
        event_type=NotificationEventType.NEW_COMMENT,
        title=f"New comment on {project.name}",
        body=comment.content[:200],
        entity_type="project",
        entity_id=str(project.id),
        recipient_keys=keys,
    )


async def notify_invoice_issued(session: AsyncSession, *, invoice_id: uuid.UUID) -> None:
    """In-app INVOICE_ISSUED push for staff (view/invoices) + the project's
    client users when the invoice is project-linked."""
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None:
        return
    keys = await staff_keys_with_permission(
        session,
        tenant_id=invoice.tenant_id,
        action="view",
        resource="invoices",
    )
    if invoice.project_id is not None:
        project = await session.get(Project, invoice.project_id)
        if project is not None:
            keys.extend(await client_keys_for_client(session, client_id=project.client_id))

    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.INVOICE_ISSUED, keys=keys
    )
    if not keys:
        return
    number = invoice.invoice_number or "unassigned"
    await notify_users(
        session,
        tenant_id=invoice.tenant_id,
        event_type=NotificationEventType.INVOICE_ISSUED,
        title=f"Invoice {number} issued",
        body="",
        entity_type="invoice",
        entity_id=str(invoice.id),
        recipient_keys=keys,
    )


async def notify_payment_recorded(
    session: AsyncSession,
    *,
    transaction_id: uuid.UUID,
) -> None:
    """In-app PAYMENT_RECEIVED push for staff (view/payments) + the project's
    client users when the invoice is project-linked."""
    tx = await session.get(Transaction, transaction_id)
    if tx is None:
        return
    invoice = await session.get(Invoice, tx.invoice_id)
    if invoice is None:
        return
    keys = await staff_keys_with_permission(
        session,
        tenant_id=invoice.tenant_id,
        action="view",
        resource="payments",
    )
    if invoice.project_id is not None:
        project = await session.get(Project, invoice.project_id)
        if project is not None:
            keys.extend(await client_keys_for_client(session, client_id=project.client_id))

    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.PAYMENT_RECEIVED, keys=keys
    )
    if not keys:
        return
    number = invoice.invoice_number or "unassigned"
    await notify_users(
        session,
        tenant_id=invoice.tenant_id,
        event_type=NotificationEventType.PAYMENT_RECEIVED,
        title=f"Payment received on invoice {number}",
        body="",
        entity_type="invoice",
        entity_id=str(invoice.id),
        recipient_keys=keys,
    )


async def notify_refund_recorded(
    session: AsyncSession,
    *,
    transaction_id: uuid.UUID,
) -> None:
    """In-app REFUND_RECORDED push for staff (view/payments) only."""
    tx = await session.get(Transaction, transaction_id)
    if tx is None:
        return
    invoice = await session.get(Invoice, tx.invoice_id)
    if invoice is None:
        return
    keys = await staff_keys_with_permission(
        session,
        tenant_id=invoice.tenant_id,
        action="view",
        resource="payments",
    )
    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.REFUND_RECORDED, keys=keys
    )
    if not keys:
        return
    number = invoice.invoice_number or "unassigned"
    await notify_users(
        session,
        tenant_id=invoice.tenant_id,
        event_type=NotificationEventType.REFUND_RECORDED,
        title=f"Refund recorded on invoice {number}",
        body="",
        entity_type="invoice",
        entity_id=str(invoice.id),
        recipient_keys=keys,
    )


async def notify_advance_applied(
    session: AsyncSession,
    *,
    invoice_id: uuid.UUID,
    amount: Decimal,
) -> None:
    """In-app ADVANCE_APPLIED push for staff (view/payments) only."""
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None:
        return
    keys = await staff_keys_with_permission(
        session,
        tenant_id=invoice.tenant_id,
        action="view",
        resource="payments",
    )
    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.ADVANCE_APPLIED, keys=keys
    )
    if not keys:
        return
    number = invoice.invoice_number or "unassigned"
    await notify_users(
        session,
        tenant_id=invoice.tenant_id,
        event_type=NotificationEventType.ADVANCE_APPLIED,
        title=f"Advance of {amount} applied to invoice {number}",
        body="",
        entity_type="invoice",
        entity_id=str(invoice.id),
        recipient_keys=keys,
    )


async def notify_milestone_completed(
    session: AsyncSession,
    *,
    milestone_id: uuid.UUID,
) -> None:
    """In-app MILESTONE_COMPLETED push for staff (view/milestones) + the
    project's client users."""
    milestone = await session.get(ProjectMilestone, milestone_id)
    if milestone is None:
        return
    project = await session.get(Project, milestone.project_id)
    if project is None:
        return
    keys = await staff_keys_with_permission(
        session,
        tenant_id=project.tenant_id,
        action="view",
        resource="milestones",
    )
    keys.extend(await client_keys_for_client(session, client_id=project.client_id))
    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.MILESTONE_COMPLETED, keys=keys
    )
    if not keys:
        return
    await notify_users(
        session,
        tenant_id=project.tenant_id,
        event_type=NotificationEventType.MILESTONE_COMPLETED,
        title=f"Milestone completed: {milestone.name}",
        body="",
        entity_type="milestone",
        entity_id=str(milestone.id),
        recipient_keys=keys,
    )


async def notify_project_created(session: AsyncSession, *, project_id: uuid.UUID) -> None:
    """In-app PROJECT_CREATED push for staff (view/projects)."""
    project = await session.get(Project, project_id)
    if project is None:
        return
    keys = await staff_keys_with_permission(
        session,
        tenant_id=project.tenant_id,
        action="view",
        resource="projects",
    )
    keys = await filter_keys_by_pref(
        session, event_type=NotificationEventType.PROJECT_CREATED, keys=keys
    )
    if not keys:
        return
    await notify_users(
        session,
        tenant_id=project.tenant_id,
        event_type=NotificationEventType.PROJECT_CREATED,
        title=f"Project created: {project.name}",
        body="",
        entity_type="project",
        entity_id=str(project.id),
        recipient_keys=keys,
    )


# ── Read API (TODO-172) ───────────────────────────────────────────────────


class NotificationNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )


async def list_notifications(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
    page: int,
    page_size: int,
    unread_only: bool | None,
) -> dict[str, Any]:
    """Paginated notification list for one user (newest first)."""
    base = select(Notification).where(
        Notification.user_id == user_id,
        Notification.user_type == user_type,
    )
    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    unread = (
        await session.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.user_type == user_type,
                Notification.is_read.is_(False),
            )
        )
    ).scalar_one()

    stmt = base.order_by(Notification.created_at.desc(), Notification.id.desc())
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "id": row.id,
                "event_type": row.event_type,
                "title": row.title,
                "body": row.body,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "data": row.data or {},
                "is_read": row.is_read,
                "created_at": row.created_at,
            }
        )
    return {
        "items": items,
        "total": total,
        "unread": unread,
        "page": page,
        "page_size": page_size,
    }


async def unread_count(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
) -> int:
    """Count unread notifications for one user."""
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.user_type == user_type,
            Notification.is_read.is_(False),
        )
    )
    return (await session.execute(stmt)).scalar_one()


async def mark_read(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
    notification_id: uuid.UUID,
) -> None:
    """Mark one notification read; 404 when it does not belong to the user."""
    row = (
        await session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.user_type == user_type,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotificationNotFoundError()
    row.is_read = True
    await session.commit()


async def mark_all_read(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    user_type: str,
) -> None:
    """Mark every unread notification of the user read; commit."""
    await session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.user_type == user_type,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await session.commit()
