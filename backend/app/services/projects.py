"""Project management business logic (FEAT-007, US-025..US-027).

Owns the orchestration of:
- Project creation with service attachment + milestone instantiation
- Project detail / list (with rollups)
- Project status / metadata updates
- Mid-project service attachment (active projects only)
- Milestone updates
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.enums import (
    ActorType,
    MilestoneStatus,
    ProjectServiceStatus,
    ProjectStatus,
)
from app.models.milestone_step_template import MilestoneStepTemplate
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService
from app.models.service import Service
from app.repositories import clients as client_repo
from app.repositories import projects as project_repo
from app.repositories import services as service_repo
from app.services.audit import log as audit_log

# ── Exceptions ──────────────────────────────────────────────────────────────


class ProjectNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


class ProjectServiceNotAttachedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project service not found",
        )


class MilestoneNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found",
        )


class ProjectServiceAlreadyAttachedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service is already attached to this project",
        )


class ProjectNotActiveError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is not Active; cannot attach services",
        )


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_client(
    session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID
) -> Client:
    client = await client_repo.get_by_tenant_id(session, tenant_id, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )
    return client


async def _get_service_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Service:
    """Verify service exists in tenant and is active. 404 otherwise."""
    service = await service_repo.get_service_for_tenant(session, tenant_id, service_id)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    return service


async def _get_admin_user(
    session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Verify an admin user exists in the same tenant. True if ok, False otherwise."""
    from app.models.admin_user import AdminUser

    user = await session.get(AdminUser, user_id)
    return user is not None and user.tenant_id == tenant_id


def _compute_planned_date(
    start_date: date | None,
    cumulative_days: int,
) -> date | None:
    """Compute planned_date = start_date + cumulative_days. None if start_date missing."""
    if start_date is None:
        return None
    return start_date + timedelta(days=cumulative_days)


async def _attach_service_internal(
    session: AsyncSession,
    project: Project,
    service: Service,
    *,
    start_date: date | None,
) -> ProjectService:
    """Create ProjectService + instantiate milestone rows from templates.

    Cumulative planned_date = start_date + sum(prior expected_duration_days)
    if both start_date and prior durations exist; else None for that step.
    """
    project_service = await project_repo.attach_service(
        session,
        project,
        service,
        price_at_attachment=service.default_price,
    )

    # Instantiate milestones in sequence order
    template_q = (
        select(MilestoneStepTemplate)
        .where(MilestoneStepTemplate.service_id == service.id)
        .order_by(MilestoneStepTemplate.sequence_order)
    )
    templates = list((await session.execute(template_q)).scalars().all())

    prior_days = 0
    for tmpl in templates:
        # planned_date = start + (prior_days + this_step_duration)
        # i.e. end of the current step. None if either side missing.
        if tmpl.expected_duration_days is not None and start_date is not None:
            planned = _compute_planned_date(
                start_date, prior_days + tmpl.expected_duration_days
            )
            prior_days += tmpl.expected_duration_days
        else:
            planned = None

        milestone = ProjectMilestone(
            project_id=project.id,
            project_service_id=project_service.id,
            service_id=service.id,
            name=tmpl.name,
            sequence_order=tmpl.sequence_order,
            status=MilestoneStatus.PENDING,
            planned_date=planned,
            description=tmpl.description,
        )
        session.add(milestone)

    await session.flush()
    return project_service


# ── CRUD ────────────────────────────────────────────────────────────────────


async def create_project(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    client_id: uuid.UUID,
    start_date: date | None = None,
    owner_id: uuid.UUID | None = None,
    service_ids: list[uuid.UUID] | None = None,
    actor_id: uuid.UUID,
) -> Project:
    """Create a project in Draft + attach services + instantiate milestones."""
    # Verify client in tenant (404 if not)
    await _get_client(session, tenant_id, client_id)

    # Verify owner belongs to tenant (if provided)
    if owner_id is not None and not await _get_admin_user(session, tenant_id, owner_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found",
        )

    # Verify + collect services in tenant
    services: list[Service] = []
    seen: set[uuid.UUID] = set()
    for sid in service_ids or []:
        if sid in seen:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate service_id in request",
            )
        seen.add(sid)
        svc = await _get_service_for_tenant(session, tenant_id, sid)
        services.append(svc)

    project = await project_repo.create_project(
        session,
        tenant_id=tenant_id,
        name=name,
        client_id=client_id,
        start_date=start_date,
        owner_id=owner_id,
    )

    for svc in services:
        await _attach_service_internal(
            session, project, svc, start_date=start_date
        )

    await session.flush()
    await session.refresh(project, attribute_names=["project_services", "milestones"])

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="project.created",
        entity_type="project",
        entity_id=str(project.id),
        details={
            "name": name,
            "client_id": str(client_id),
            "service_count": len(services),
        },
    )

    await session.commit()
    return project


async def get_project(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project:
    """Get project with services + milestones eager-loaded. 404 if not found."""
    project = await project_repo.get_project_for_tenant_with_services(
        session, tenant_id, project_id
    )
    if project is None:
        raise ProjectNotFoundError()
    return project


async def list_projects(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: ProjectStatus | None = None,
    client_id: uuid.UUID | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    """List projects for a tenant. Returns items with rollup counts."""
    items, total = await project_repo.list_projects_for_tenant(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status=status_filter,
        client_id=client_id,
        sort=sort,
    )

    result_items: list[dict[str, Any]] = []
    for p in items:
        active_services = [s for s in p.project_services if s.status == ProjectServiceStatus.ACTIVE]
        milestones = p.milestones
        completed = sum(1 for m in milestones if m.status == MilestoneStatus.COMPLETED)
        result_items.append(
            {
                "id": p.id,
                "name": p.name,
                "client_id": p.client_id,
                "status": p.status,
                "start_date": p.start_date,
                "owner_id": p.owner_id,
                "service_count": len(active_services),
                "milestone_total": len(milestones),
                "milestone_completed": completed,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
        )

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def update_project(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    updates: dict[str, Any],
    actor_id: uuid.UUID,
) -> Project:
    """Update project fields. Tenant + name length validated."""
    project = await project_repo.get_project_for_tenant(session, tenant_id, project_id)
    if project is None:
        raise ProjectNotFoundError()

    # If owner_id being changed, verify new owner in tenant
    if (
        "owner_id" in updates
        and updates["owner_id"] is not None
        and not await _get_admin_user(session, tenant_id, updates["owner_id"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner not found",
        )

    # Drop None values
    filtered = {k: v for k, v in updates.items() if v is not None}
    if not filtered:
        return await _reload_with_relations(session, project)

    changed_keys: list[str] = []
    for key, val in filtered.items():
        old_val = getattr(project, key, None)
        if old_val != val:
            changed_keys.append(key)
            setattr(project, key, val)

    if changed_keys:
        await session.flush()
        await session.refresh(project)

        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="project.updated",
            entity_type="project",
            entity_id=str(project.id),
            details={"changed_keys": changed_keys},
        )

        await session.commit()

    return await _reload_with_relations(session, project)


async def _reload_with_relations(
    session: AsyncSession, project: Project
) -> Project:
    """Re-fetch project with services+milestones eager-loaded."""
    fresh = await project_repo.get_project_for_tenant_with_services(
        session, project.tenant_id, project.id
    )
    return fresh if fresh is not None else project


# ── Attach service to existing project ─────────────────────────────────────


async def attach_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    service_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> tuple[ProjectService, int]:
    """Attach a service to an Active project. 404 / 409 as appropriate.

    Returns (project_service, milestone_count).
    """
    project = await project_repo.get_project_for_tenant(session, tenant_id, project_id)
    if project is None:
        raise ProjectNotFoundError()

    if project.status != ProjectStatus.ACTIVE:
        raise ProjectNotActiveError()

    service = await _get_service_for_tenant(session, tenant_id, service_id)

    # Check existing attachment (unique constraint would catch, but raise clean 409)
    existing_q = select(ProjectService).where(
        ProjectService.project_id == project_id,
        ProjectService.service_id == service_id,
    )
    existing = (await session.execute(existing_q)).scalar_one_or_none()
    if existing is not None:
        raise ProjectServiceAlreadyAttachedError()

    project_service = await _attach_service_internal(
        session, project, service, start_date=project.start_date
    )

    # Count the milestones we just added (in DB after flush)
    count_q = select(ProjectMilestone).where(
        ProjectMilestone.project_service_id == project_service.id
    )
    milestone_count = len(list((await session.execute(count_q)).scalars().all()))

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="project.service_attached",
        entity_type="project",
        entity_id=str(project.id),
        details={
            "service_id": str(service_id),
            "milestone_count": milestone_count,
        },
    )

    await session.commit()
    await session.refresh(project_service)
    return project_service, milestone_count


# ── Milestone ops ───────────────────────────────────────────────────────────


async def get_milestone(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    milestone_id: uuid.UUID,
) -> ProjectMilestone:
    milestone = await project_repo.get_milestone_for_tenant(
        session, tenant_id, milestone_id
    )
    if milestone is None:
        raise MilestoneNotFoundError()
    return milestone


async def update_milestone(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    milestone_id: uuid.UUID,
    updates: dict[str, Any],
    actor_id: uuid.UUID,
) -> ProjectMilestone:
    """Update milestone fields. Validates assignee belongs to tenant."""
    milestone = await project_repo.get_milestone_for_tenant(
        session, tenant_id, milestone_id
    )
    if milestone is None:
        raise MilestoneNotFoundError()

    # If assignee_id being set, verify tenant membership
    if (
        "assignee_id" in updates
        and updates["assignee_id"] is not None
        and not await _get_admin_user(session, tenant_id, updates["assignee_id"])
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignee not found",
        )

    filtered = {k: v for k, v in updates.items() if v is not None}
    if not filtered:
        return milestone

    changed_keys: list[str] = []
    for key, val in filtered.items():
        old_val = getattr(milestone, key, None)
        if old_val != val:
            changed_keys.append(key)
            setattr(milestone, key, val)

    if changed_keys:
        await session.flush()
        await session.refresh(milestone)

        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="project.milestone_updated",
            entity_type="project_milestone",
            entity_id=str(milestone.id),
            details={
                "project_id": str(milestone.project_id),
                "changed_keys": changed_keys,
            },
        )

        await session.commit()

    return milestone
