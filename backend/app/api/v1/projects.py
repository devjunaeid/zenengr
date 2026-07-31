"""Tenant-scoped project management endpoints (FEAT-007).

Base path: /api/v1/tenant/projects
Guards: manage/projects = admin+manager for writes; all staff can read.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import ProjectStatus
from app.schemas.projects import (
    AttachServiceRequest,
    AttachServiceResponse,
    MilestoneUpdateRequest,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectListResponse,
    ProjectMilestoneItem,
    ProjectServiceItem,
    ProjectUpdateRequest,
)
from app.services import projects as project_service

router = APIRouter(prefix="/tenant/projects", tags=["projects"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


def _build_service_items(project: Any) -> list[ProjectServiceItem]:
    """Build ProjectServiceItem list with cross-relation service_name."""
    items: list[ProjectServiceItem] = []
    for ps in project.project_services:
        items.append(
            ProjectServiceItem(
                id=ps.id,
                service_id=ps.service_id,
                service_name=ps.service.name if ps.service else "",
                status=ps.status,
                price_at_attachment=ps.price_at_attachment,
                created_at=ps.created_at,
                updated_at=ps.updated_at,
            )
        )
    return items


def _build_milestone_items(project: Any) -> list[ProjectMilestoneItem]:
    items: list[ProjectMilestoneItem] = []
    for m in project.milestones:
        items.append(
            ProjectMilestoneItem(
                id=m.id,
                project_service_id=m.project_service_id,
                service_id=m.service_id,
                name=m.name,
                sequence_order=m.sequence_order,
                status=m.status,
                planned_date=m.planned_date,
                actual_date=m.actual_date,
                assignee_id=m.assignee_id,
                description=m.description,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return items


def _to_detail(project: Any) -> ProjectDetailResponse:
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        client_id=project.client_id,
        status=project.status,
        start_date=project.start_date,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        services=_build_service_items(project),
        milestones=_build_milestone_items(project),
    )


def _to_create_response(project: Any) -> ProjectCreateResponse:
    return ProjectCreateResponse(
        id=project.id,
        name=project.name,
        client_id=project.client_id,
        status=project.status,
        start_date=project.start_date,
        owner_id=project.owner_id,
        service_count=len(project.project_services),
        milestone_count=len(project.milestones),
        created_at=project.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_endpoint(
    body: ProjectCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> ProjectCreateResponse:
    """Create a project with optional service attachments. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    project = await project_service.create_project(
        session,
        tenant_id=tenant_id,
        name=body.name,
        client_id=body.client_id,
        start_date=body.start_date,
        owner_id=body.owner_id,
        service_ids=body.service_ids,
        actor_id=user.id,
    )
    return _to_create_response(project)


@router.get("/", response_model=ProjectListResponse)
async def list_projects_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_val: str | None = Query(default=None, alias="status"),
    client_id: str | None = Query(default=None),
    sort: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ProjectListResponse:
    """List projects for a tenant. All staff can read."""
    tenant_id = _get_tenant_id(user)

    status_filter: ProjectStatus | None = None
    if status_val:
        try:
            status_filter = ProjectStatus(status_val)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid status: {status_val}. "
                    "Must be 'draft', 'active', 'on_hold', 'completed', or 'cancelled'."
                ),
            ) from None

    parsed_client_id: uuid.UUID | None = None
    if client_id:
        try:
            parsed_client_id = uuid.UUID(client_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="client_id must be a valid UUID",
            ) from exc

    result = await project_service.list_projects(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        client_id=parsed_client_id,
        sort=sort,
    )

    items = [ProjectListItem(**item) for item in result["items"]]
    return ProjectListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ProjectDetailResponse:
    """Get project detail with services + milestones. All staff can read."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    project = await project_service.get_project(
        session, tenant_id=tenant_id, project_id=pid
    )
    return _to_detail(project)


@router.patch("/{project_id}", response_model=ProjectDetailResponse)
async def update_project_endpoint(
    project_id: str,
    body: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> ProjectDetailResponse:
    """Update project fields. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")

    updates = body.model_dump(exclude_unset=True)
    project = await project_service.update_project(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        updates=updates,
        actor_id=user.id,
    )
    return _to_detail(project)


# ═══════════════════════════════════════════════════════════════════════════
# Attach service
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{project_id}/services",
    response_model=AttachServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_service_endpoint(
    project_id: str,
    body: AttachServiceRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> AttachServiceResponse:
    """Attach a service to an Active project. Instantiates milestones. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")

    project_service_row, milestone_count = await project_service.attach_service(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        service_id=body.service_id,
        actor_id=user.id,
    )
    return AttachServiceResponse(
        project_service_id=project_service_row.id,
        service_id=project_service_row.service_id,
        service_name=project_service_row.service.name
        if project_service_row.service
        else "",
        milestone_count=milestone_count,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Milestone update
# ═══════════════════════════════════════════════════════════════════════════


@router.patch(
    "/{project_id}/milestones/{milestone_id}",
    response_model=ProjectMilestoneItem,
)
async def update_milestone_endpoint(
    project_id: str,
    milestone_id: str,
    body: MilestoneUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "milestones")),
) -> ProjectMilestoneItem:
    """Update milestone fields. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    # Validate path UUIDs (404 on bad format)
    _parse_uuid(project_id, kind="Project")
    mid = _parse_uuid(milestone_id, kind="Milestone")

    updates = body.model_dump(exclude_unset=True)
    milestone = await project_service.update_milestone(
        session,
        tenant_id=tenant_id,
        milestone_id=mid,
        updates=updates,
        actor_id=user.id,
    )
    return ProjectMilestoneItem(
        id=milestone.id,
        project_service_id=milestone.project_service_id,
        service_id=milestone.service_id,
        name=milestone.name,
        sequence_order=milestone.sequence_order,
        status=milestone.status,
        planned_date=milestone.planned_date,
        actual_date=milestone.actual_date,
        assignee_id=milestone.assignee_id,
        description=milestone.description,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )
