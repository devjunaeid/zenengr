"""Project repository -- thin data access layer for FEAT-007.

All read functions are tenant-scoped. Cross-tenant access returns None.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.enums import MilestoneStatus, ProjectServiceStatus, ProjectStatus
from app.models.project import Project, ProjectMember
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService

# ── Project lookups ─────────────────────────────────────────────────────────


async def get_project_by_id(
    session: AsyncSession, project_id: uuid.UUID
) -> Project | None:
    """Fetch a project by PK (tenant un-isolated internal helper)."""
    stmt = select(Project).where(Project.id == project_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_project_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project | None:
    """Fetch a project by id scoped to a tenant. No relations loaded."""
    stmt = select(Project).where(
        Project.id == project_id, Project.tenant_id == tenant_id
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_project_for_tenant_with_services(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project | None:
    """Fetch a project with services (eager-loaded with their Service) + milestones + members.

    Used by get/detail endpoints to build full response without N+1.
    """
    stmt = (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.project_services).selectinload(ProjectService.service),
            selectinload(Project.milestones),
            selectinload(Project.members).selectinload(ProjectMember.user),
        )
        .where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def search_projects_picker(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    q: str | None = None,
    client_id: uuid.UUID | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Fast, lean project lookup for dropdowns and pickers (id, name, client_id, client_name)."""
    query = (
        select(
            Project.id,
            Project.name,
            Project.client_id,
            Project.status,
            Client.name.label("client_name"),
        )
        .outerjoin(Client, Client.id == Project.client_id)
        .where(Project.tenant_id == tenant_id)
    )
    if client_id is not None:
        query = query.where(Project.client_id == client_id)
    if q and q.strip():
        search_term = q.strip().lstrip("#")
        pattern = f"%{search_term}%"
        query = query.where(
            or_(
                Project.name.ilike(pattern),
                Client.name.ilike(pattern),
                cast(Project.id, String).ilike(pattern),
            )
        )
    query = query.order_by(Project.name.asc()).limit(limit)
    result = await session.execute(query)
    rows = result.mappings().all()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "client_id": r["client_id"],
            "status": r["status"],
            "client_name": r["client_name"],
        }
        for r in rows
    ]


async def list_projects_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: ProjectStatus | None = None,
    client_id: uuid.UUID | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """List projects for a tenant with filters + pagination using single-query SQL pushdown aggregation."""
    count_q = select(func.count(Project.id)).where(Project.tenant_id == tenant_id)

    search_filter = None
    if status is not None:
        count_q = count_q.where(Project.status == status)
    if client_id is not None:
        count_q = count_q.where(Project.client_id == client_id)
    if q and q.strip():
        search_term = q.strip().lstrip("#")
        search_filter = or_(
            Project.name.ilike(f"%{search_term}%"),
            cast(Project.id, String).ilike(f"%{search_term}%"),
        )
        count_q = count_q.where(search_filter)

    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    if total == 0:
        return [], 0

    # Subqueries for active service count and milestone stats
    svc_sub = (
        select(
            ProjectService.project_id,
            func.count().label("service_count"),
        )
        .where(ProjectService.status == ProjectServiceStatus.ACTIVE)
        .group_by(ProjectService.project_id)
        .subquery()
    )
    ms_sub = (
        select(
            ProjectMilestone.project_id,
            func.count().label("milestone_total"),
            func.count()
            .filter(ProjectMilestone.status == MilestoneStatus.COMPLETED)
            .label("milestone_completed"),
        )
        .group_by(ProjectMilestone.project_id)
        .subquery()
    )

    query = (
        select(
            Project.id,
            Project.name,
            Project.client_id,
            Project.status,
            Project.start_date,
            Project.owner_id,
            Project.auto_invoice,
            Project.created_at,
            Project.updated_at,
            func.coalesce(svc_sub.c.service_count, 0).label("service_count"),
            func.coalesce(ms_sub.c.milestone_total, 0).label("milestone_total"),
            func.coalesce(ms_sub.c.milestone_completed, 0).label("milestone_completed"),
        )
        .outerjoin(svc_sub, svc_sub.c.project_id == Project.id)
        .outerjoin(ms_sub, ms_sub.c.project_id == Project.id)
        .where(Project.tenant_id == tenant_id)
    )

    if status is not None:
        query = query.where(Project.status == status)
    if client_id is not None:
        query = query.where(Project.client_id == client_id)
    if search_filter is not None:
        query = query.where(search_filter)

    # Sort
    if sort:
        desc = sort.startswith("-")
        col_name = sort.lstrip("-")
        col = getattr(Project, col_name, None)
        if col is not None:
            query = query.order_by(col.desc() if desc else col.asc())
        else:
            query = query.order_by(Project.created_at.desc())
    else:
        query = query.order_by(Project.created_at.desc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    rows = result.mappings().all()

    items = [
        {
            "id": r["id"],
            "name": r["name"],
            "client_id": r["client_id"],
            "status": r["status"],
            "start_date": r["start_date"],
            "owner_id": r["owner_id"],
            "auto_invoice": r["auto_invoice"],
            "service_count": r["service_count"],
            "milestone_total": r["milestone_total"],
            "milestone_completed": r["milestone_completed"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    return items, total


async def create_project(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    client_id: uuid.UUID,
    start_date: Any = None,
    owner_id: uuid.UUID | None = None,
) -> Project:
    """Insert a new project row in Draft status."""
    project = Project(
        tenant_id=tenant_id,
        name=name,
        client_id=client_id,
        status=ProjectStatus.DRAFT,
        start_date=start_date,
        owner_id=owner_id,
    )
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def update_project(
    session: AsyncSession,
    project: Project,
    **kwargs: Any,
) -> Project:
    """Update project fields. Caller must flush."""
    for key, val in kwargs.items():
        setattr(project, key, val)
    await session.flush()
    await session.refresh(project)
    return project


# ── ProjectService lookups ──────────────────────────────────────────────────


async def get_project_service(
    session: AsyncSession,
    project_service_id: uuid.UUID,
) -> ProjectService | None:
    """Fetch a project_service by primary key (no tenant scope)."""
    stmt = select(ProjectService).where(ProjectService.id == project_service_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_project_service_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_service_id: uuid.UUID,
) -> ProjectService | None:
    """Fetch project_service scoped via project.tenant_id."""
    stmt = (
        select(ProjectService)
        .join(Project, ProjectService.project_id == Project.id)
        .where(
            ProjectService.id == project_service_id,
            Project.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def attach_service(
    session: AsyncSession,
    project: Project,
    service: Any,
    *,
    price_at_attachment: Decimal | None,
) -> ProjectService:
    """Create a ProjectService row linking project + service."""
    project_service = ProjectService(
        project_id=project.id,
        service_id=service.id,
        price_at_attachment=price_at_attachment,
    )
    session.add(project_service)
    await session.flush()
    await session.refresh(project_service)
    return project_service


async def cancel_project_service(
    session: AsyncSession,
    project_service: ProjectService,
) -> None:
    """Mark a project_service as cancelled (soft). No delete."""
    from app.models.enums import ProjectServiceStatus

    project_service.status = ProjectServiceStatus.CANCELLED
    await session.flush()
    await session.refresh(project_service)


async def delete_project_service(
    session: AsyncSession,
    project_service: ProjectService,
) -> None:
    """Hard-delete a project_service; milestones cascade via relationship + FK."""
    await session.delete(project_service)
    await session.flush()


# ── Milestone lookups ──────────────────────────────────────────────────────


async def get_milestone_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    milestone_id: uuid.UUID,
) -> ProjectMilestone | None:
    """Fetch a milestone scoped via project.tenant_id."""
    stmt = (
        select(ProjectMilestone)
        .join(Project, ProjectMilestone.project_id == Project.id)
        .where(
            ProjectMilestone.id == milestone_id,
            Project.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_milestone(
    session: AsyncSession,
    milestone: ProjectMilestone,
    **kwargs: Any,
) -> ProjectMilestone:
    """Update milestone fields. Caller must flush."""
    for key, val in kwargs.items():
        setattr(milestone, key, val)
    await session.flush()
    await session.refresh(milestone)
    return milestone
