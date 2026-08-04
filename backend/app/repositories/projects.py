"""Project repository -- thin data access layer for FEAT-007.

All read functions are tenant-scoped. Cross-tenant access returns None.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService

# ── Project lookups ─────────────────────────────────────────────────────────


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
    """Fetch a project with services (eager-loaded with their Service) + milestones.

    Used by get/detail endpoints to build full response without N+1.
    """
    stmt = (
        select(Project)
        .options(
            selectinload(Project.project_services).selectinload(ProjectService.service),
            selectinload(Project.milestones),
        )
        .where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def list_projects_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: ProjectStatus | None = None,
    client_id: uuid.UUID | None = None,
    sort: str | None = None,
) -> tuple[list[Project], int]:
    """List projects for a tenant with filters + pagination. Eager-loads
    project_services + milestones for rollup counts."""
    query = select(Project).options(
        selectinload(Project.project_services),
        selectinload(Project.milestones),
    ).where(Project.tenant_id == tenant_id)

    if status is not None:
        query = query.where(Project.status == status)
    if client_id is not None:
        query = query.where(Project.client_id == client_id)

    # Count (strip options to avoid double-counting in joined query)
    count_q = select(func.count()).select_from(
        select(Project).where(Project.tenant_id == tenant_id).subquery()
    )
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

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
    items = list(result.unique().scalars().all())

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
