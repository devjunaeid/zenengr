"""Project comment business logic (FEAT-010, TODO-100/103/104/106/107).

Owns the orchestration of:
- Tenant comment posting (internal vs shared) with role rules: employees
  may only comment on projects they own; admin/manager may comment anywhere
- Listing comments: staff see internal + shared, clients see shared only
- Audit trail + notification dispatch for every comment
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_user import AdminUser
from app.models.client_user import ClientUser
from app.models.comment import Comment
from app.models.enums import ActorType, AdminUserRole, CommentAuthorType
from app.models.project import Project
from app.services import notifications
from app.services.audit import log as audit_log

# ── Exceptions ──────────────────────────────────────────────────────────────


class CommentProjectNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


class CommentForbiddenError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions for this project",
        )


class CommentContentError(HTTPException):
    """Backstop; the request schema min_length normally covers this."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Comment content cannot be empty",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _author_type_for_role(role: AdminUserRole) -> CommentAuthorType:
    if role == AdminUserRole.ADMIN:
        return CommentAuthorType.TENANT_ADMIN
    if role == AdminUserRole.MANAGER:
        return CommentAuthorType.TENANT_MANAGER
    if role == AdminUserRole.EMPLOYEE:
        return CommentAuthorType.TENANT_EMPLOYEE
    return CommentAuthorType.TENANT_ADMIN


async def _get_project_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project | None:
    stmt = select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_project_for_client(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project | None:
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_id == tenant_id,
        Project.client_id == client_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ── CRUD ────────────────────────────────────────────────────────────────────


async def post_comment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    content: str,
    is_internal: bool,
    actor: AdminUser,
) -> Comment:
    """Post a tenant comment. Permission decided at the endpoint layer
    (FEAT-016: no employee/owner restriction — any staff may comment)."""
    project = await _get_project_for_tenant(session, tenant_id, project_id)
    if project is None:
        raise CommentProjectNotFoundError()

    content = content.strip()
    if not content:
        raise CommentContentError()

    is_internal = bool(is_internal)
    comment = Comment(
        project_id=project_id,
        author_id=actor.id,
        author_type=_author_type_for_role(actor.role),
        author_name=actor.full_name,
        content=content,
        is_internal=is_internal,
    )
    session.add(comment)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_type=ActorType.ADMIN_USER,
        action="comment.created",
        entity_type="comment",
        entity_id=str(comment.id),
        details={"project_id": str(project_id), "is_internal": is_internal},
    )

    if not is_internal:
        await notifications.dispatch_new_comment(
            session,
            project_id=project_id,
            comment=comment,
            excludes_user_id=actor.id,
            tenant_id=tenant_id,
        )

    await session.commit()
    return comment


async def list_comments(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[Comment]:
    """List comments for a project (staff see internal + shared), oldest first."""
    project = await _get_project_for_tenant(session, tenant_id, project_id)
    if project is None:
        raise CommentProjectNotFoundError()

    stmt = (
        select(Comment).where(Comment.project_id == project_id).order_by(Comment.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def post_client_comment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    project_id: uuid.UUID,
    content: str,
    actor: ClientUser,
) -> Comment:
    """Post a client comment. Project must belong to the caller's client.

    Client comments are always shared (is_internal forced False).
    """
    project = await _get_project_for_client(
        session, tenant_id=tenant_id, client_id=client_id, project_id=project_id
    )
    if project is None:
        raise CommentProjectNotFoundError()

    content = content.strip()
    if not content:
        raise CommentContentError()

    comment = Comment(
        project_id=project_id,
        author_id=actor.id,
        author_type=CommentAuthorType.CLIENT_USER,
        author_name=actor.full_name,
        content=content,
        is_internal=False,
    )
    session.add(comment)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor.id,
        actor_type=ActorType.CLIENT_USER,
        action="comment.created",
        entity_type="comment",
        entity_id=str(comment.id),
        details={"project_id": str(project_id), "is_internal": False},
    )

    await notifications.dispatch_new_comment(
        session,
        project_id=project_id,
        comment=comment,
        excludes_user_id=actor.id,
        tenant_id=tenant_id,
    )

    await session.commit()
    return comment


async def list_client_comments(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[Comment]:
    """List shared comments for a client's project, oldest first."""
    project = await _get_project_for_client(
        session, tenant_id=tenant_id, client_id=client_id, project_id=project_id
    )
    if project is None:
        raise CommentProjectNotFoundError()

    stmt = (
        select(Comment)
        .where(Comment.project_id == project_id, Comment.is_internal.is_(False))
        .order_by(Comment.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
