"""Notification dispatch (FEAT-010, TODO-107).

TODO-108/TODO-116: recipients are filtered by their per-user
NotificationPreference for the event type (missing = default enabled).
Email failures are swallowed so a notification problem never breaks the
primary action (comment post).
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.admin_user import AdminUser
from app.models.client_user import ClientUser
from app.models.comment import Comment
from app.models.enums import NotificationEventType
from app.models.project import Project
from app.services.notification_preferences import get_enabled_map
from app.services.smtp import send_tenant_email

logger = logging.getLogger(__name__)


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
            user_type="admin_user",
            user_ids=admin_ids,
            event_type=NotificationEventType.NEW_COMMENT,
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
            user_type="client_user",
            user_ids=client_ids,
            event_type=NotificationEventType.NEW_COMMENT,
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
