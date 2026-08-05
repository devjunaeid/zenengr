"""Client-scoped project comment endpoints (FEAT-010, TODO-100/103/104/106/107).

Base path: /api/v1/client/projects
Client users see only shared comments on their own client's projects and
post shared comments only (is_internal is forced False server-side).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_client_user
from app.db.session import get_session
from app.models.client_user import ClientUser
from app.models.enums import MilestoneStatus, ProjectStatus
from app.models.file_asset import FileAsset
from app.models.project import Project
from app.models.project_service import ProjectService
from app.schemas.client_portal import (
    ClientProjectDetailResponse,
    ClientProjectFinancialSummary,
    ClientProjectListItem,
    ClientProjectListResponse,
    ClientProjectMilestoneItem,
    ClientProjectServiceItem,
)
from app.schemas.comments import CommentCreateRequest, CommentResponse
from app.schemas.files import FileAssetItem, FileListResponse
from app.schemas.projects import LinkedInvoiceItem
from app.services import comments as comment_service
from app.services import files as files_service
from app.services import financials as financials_service

router = APIRouter(prefix="/client/projects", tags=["client-projects"])


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


def _to_comment_response(comment: Any) -> CommentResponse:
    return CommentResponse(
        id=comment.id,
        project_id=comment.project_id,
        author_id=comment.author_id,
        author_type=comment.author_type,
        author_name=comment.author_name,
        content=comment.content,
        is_internal=comment.is_internal,
        created_at=comment.created_at,
    )


def _to_asset_item(asset: FileAsset) -> FileAssetItem:
    return FileAssetItem(
        id=asset.id,
        name=asset.name,
        scope=asset.scope,
        folder_id=asset.folder_id,
        project_id=asset.project_id,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        created_by_id=asset.created_by_id,
        created_by_type=asset.created_by_type,
        created_at=asset.created_at,
    )


def _milestone_counts(project: Project) -> tuple[int, int]:
    total = len(project.milestones)
    completed = sum(1 for m in project.milestones if m.status == MilestoneStatus.COMPLETED)
    return total, completed


def _completion_pct(total: int, completed: int) -> float:
    if total == 0:
        return 0.0
    return round(completed / total * 100, 2)


def _to_list_item(project: Project) -> ClientProjectListItem:
    total, completed = _milestone_counts(project)
    return ClientProjectListItem(
        id=project.id,
        name=project.name,
        status=project.status,
        start_date=project.start_date,
        milestone_total=total,
        milestone_completed=completed,
        milestone_completion_pct=_completion_pct(total, completed),
        created_at=project.created_at,
    )


@router.get("/", response_model=ClientProjectListResponse)
async def list_client_projects_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_val: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> ClientProjectListResponse:
    """List the client's own projects with milestone completion rollups."""
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

    base = (
        select(Project)
        .options(
            selectinload(Project.project_services),
            selectinload(Project.milestones),
        )
        .where(
            Project.client_id == user.client_id,
            Project.tenant_id == user.tenant_id,
        )
    )
    if status_filter is not None:
        base = base.where(Project.status == status_filter)

    total: int = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    result = await session.execute(
        base.order_by(Project.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    projects = list(result.unique().scalars().all())

    return ClientProjectListResponse(
        items=[_to_list_item(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", response_model=ClientProjectDetailResponse)
async def get_client_project_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> ClientProjectDetailResponse:
    """Project detail scoped to the client: services, milestones, financials.

    404 for projects that do not belong to the caller's client (leak prevention).
    """
    pid = _parse_uuid(project_id, kind="Project")
    stmt = (
        select(Project)
        .options(
            selectinload(Project.project_services).selectinload(ProjectService.service),
            selectinload(Project.milestones),
        )
        .where(
            Project.id == pid,
            Project.client_id == user.client_id,
            Project.tenant_id == user.tenant_id,
        )
    )
    result = await session.execute(stmt)
    project = result.unique().scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    total, completed = _milestone_counts(project)
    financials = await financials_service.get_project_financials(session, project_id=project.id)
    invoices = await financials_service.list_linked_invoices(session, project_id=project.id)

    services = [
        ClientProjectServiceItem(
            id=ps.id,
            service_name=ps.service.name if ps.service else "",
            status=ps.status,
            price_at_attachment=f"{ps.price_at_attachment:.2f}"
            if ps.price_at_attachment is not None
            else None,
        )
        for ps in project.project_services
    ]
    milestones = [
        ClientProjectMilestoneItem(
            id=m.id,
            name=m.name,
            sequence_order=m.sequence_order,
            status=m.status,
            planned_date=m.planned_date,
            actual_date=m.actual_date,
            assignee_id=m.assignee_id,
        )
        for m in project.milestones
    ]

    return ClientProjectDetailResponse(
        id=project.id,
        name=project.name,
        status=project.status,
        start_date=project.start_date,
        client_id=project.client_id,
        milestone_total=total,
        milestone_completed=completed,
        milestone_completion_pct=_completion_pct(total, completed),
        services=services,
        milestones=milestones,
        financials=ClientProjectFinancialSummary(
            total_invoiced=financials["total_invoiced"],
            total_paid=financials["total_paid"],
            balance_due=financials["balance_due"],
        ),
        linked_invoices=[LinkedInvoiceItem(**inv) for inv in invoices],
    )


@router.get("/{project_id}/files", response_model=FileListResponse)
async def list_client_project_files_endpoint(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> FileListResponse:
    """List PROJECT-scope files on one of the client's own projects.

    404 for projects that do not belong to the caller's client (leak prevention).
    """
    pid = _parse_uuid(project_id, kind="Project")
    result = await files_service.list_project_files_for_client(
        session,
        tenant_id=user.tenant_id,
        client_id=user.client_id,
        project_id=pid,
        page=page,
        page_size=page_size,
    )
    return FileListResponse(
        items=[_to_asset_item(item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{project_id}/comments", response_model=list[CommentResponse])
async def list_client_comments_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> list[CommentResponse]:
    """List shared comments on one of the client's projects."""
    pid = _parse_uuid(project_id, kind="Project")
    comments = await comment_service.list_client_comments(
        session,
        tenant_id=user.tenant_id,
        client_id=user.client_id,
        project_id=pid,
    )
    return [_to_comment_response(c) for c in comments]


@router.post(
    "/{project_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_client_comment_endpoint(
    project_id: str,
    body: CommentCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> CommentResponse:
    """Post a shared comment on one of the client's projects.

    is_internal in the body is ignored; client comments are always shared.
    """
    pid = _parse_uuid(project_id, kind="Project")
    comment = await comment_service.post_client_comment(
        session,
        tenant_id=user.tenant_id,
        client_id=user.client_id,
        project_id=pid,
        content=body.content,
        actor=user,
    )
    return _to_comment_response(comment)
