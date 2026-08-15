"""Tenant-scoped project management endpoints (FEAT-007).

Base path: /api/v1/tenant/projects
Guards: manage/projects = admin+manager for writes; all staff can read.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import ProjectStatus
from app.schemas.comments import CommentCreateRequest, CommentEditRequest, CommentResponse
from app.schemas.ledger import (
    AdjustmentCreateRequest,
    DiscountResponse,
    DiscountUpdateRequest,
    LedgerEntryResponse,
    ProjectLedgerResponse,
    SummaryResponse,
)
from app.schemas.projects import (
    AttachServiceRequest,
    AttachServiceResponse,
    LinkedInvoiceItem,
    MilestoneUpdateRequest,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectDetailResponse,
    ProjectListItem,
    ProjectListResponse,
    ProjectMilestoneItem,
    ProjectOverviewResponse,
    ProjectServiceFinancialItem,
    ProjectServiceItem,
    ProjectUpdateRequest,
)
from app.services import comments as comment_service
from app.services import ledger as ledger_service
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
        service_prices=body.service_prices,
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
    project = await project_service.get_project(session, tenant_id=tenant_id, project_id=pid)
    return _to_detail(project)


@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
async def get_project_overview_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ProjectOverviewResponse:
    """Project overview with milestone completion and financial summary. All staff can read."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    data = await project_service.get_project_overview(session, tenant_id=tenant_id, project_id=pid)
    return ProjectOverviewResponse(
        project_id=data["project_id"],
        name=data["name"],
        status=data["status"],
        milestone_total=data["milestone_total"],
        milestone_completed=data["milestone_completed"],
        milestone_completion_pct=data["milestone_completion_pct"],
        total_invoiced=data["financials"]["total_invoiced"],
        total_paid=data["financials"]["total_paid"],
        balance_due=data["financials"]["balance_due"],
        linked_invoices=[LinkedInvoiceItem(**inv) for inv in data["invoices"]],
        service_breakdown=[
            ProjectServiceFinancialItem(**item) for item in data["service_breakdown"]
        ],
    )


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
        price=body.price,
    )
    return AttachServiceResponse(
        project_service_id=project_service_row.id,
        service_id=project_service_row.service_id,
        service_name=project_service_row.service.name if project_service_row.service else "",
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


# ═══════════════════════════════════════════════════════════════════════════
# Remove project service (TODO-070)
# ═══════════════════════════════════════════════════════════════════════════


@router.delete(
    "/{project_id}/services/{project_service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_service_endpoint(
    project_id: str,
    project_service_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> Response:
    """Remove a project service: hard-delete when uninvoiced, soft-cancel otherwise."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    psid = _parse_uuid(project_service_id, kind="Project service")
    await project_service.remove_project_service(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        project_service_id=psid,
        actor_id=user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════════
# Project ledger (FEAT-018, TODO-179/180/181/182)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/{project_id}/ledger", response_model=ProjectLedgerResponse)
async def get_project_ledger_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> ProjectLedgerResponse:
    """Project ledger: merged charges + derived payments/refunds + live summary.

    All staff can read.
    """
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    data = await ledger_service.get_project_ledger(session, tenant_id=tenant_id, project_id=pid)
    return ProjectLedgerResponse(
        entries=[LedgerEntryResponse(**entry) for entry in data["entries"]],
        summary=SummaryResponse(**data["summary"]),
    )


@router.patch("/{project_id}/discount", response_model=DiscountResponse)
async def update_project_discount_endpoint(
    project_id: str,
    body: DiscountUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> DiscountResponse:
    """Replace (or clear) the project's single active discount. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    project = await ledger_service.set_project_discount(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
        actor_id=user.id,
    )
    return DiscountResponse(
        discount_type=project.discount_type,
        discount_value=(
            f"{project.discount_value:.2f}" if project.discount_value is not None else None
        ),
    )


@router.post(
    "/{project_id}/ledger/adjustments",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_manual_adjustment_endpoint(
    project_id: str,
    body: AdjustmentCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> LedgerEntryResponse:
    """Record a signed manual adjustment on the project ledger. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    entry = await ledger_service.add_manual_adjustment(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        amount=body.amount,
        description=body.description,
        actor_id=user.id,
    )
    return LedgerEntryResponse(
        id=entry.id,
        type=entry.type,
        amount=f"{entry.amount:.2f}",
        description=entry.description,
        source_type=entry.source_type,
        source_id=entry.source_id,
        invoice_ref=entry.invoice_ref,
        invoice_number=None,
        entry_date=entry.entry_date,
        created_at=entry.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Comments (FEAT-010, TODO-100/103/104/106/107)
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{project_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_comment_endpoint(
    project_id: str,
    body: CommentCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("post", "comments")),
) -> CommentResponse:
    """Post a comment on a project. Any staff with post/comments may post
    (FEAT-016/010: employee/owner restriction removed)."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    comment = await comment_service.post_comment(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        content=body.content,
        is_internal=body.is_internal,
        actor=user,
    )
    return _to_comment_response(comment)


@router.patch("/{project_id}/comments/{comment_id}", response_model=CommentResponse)
async def edit_comment_endpoint(
    project_id: str,
    comment_id: str,
    body: CommentEditRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("edit", "comments")),
) -> CommentResponse:
    """Edit a comment's content. Staff with edit/comments only."""
    tenant_id = _get_tenant_id(user)
    # Validate path UUIDs (404 on bad format)
    _parse_uuid(project_id, kind="Project")
    cid = _parse_uuid(comment_id, kind="Comment")
    comment = await comment_service.edit_comment(
        session,
        tenant_id=tenant_id,
        comment_id=cid,
        content=body.content,
        actor_id=user.id,
    )
    return _to_comment_response(comment)


@router.delete(
    "/{project_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment_endpoint(
    project_id: str,
    comment_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("edit", "comments")),
) -> Response:
    """Delete a comment. Staff with edit/comments only."""
    tenant_id = _get_tenant_id(user)
    # Validate path UUIDs (404 on bad format)
    _parse_uuid(project_id, kind="Project")
    cid = _parse_uuid(comment_id, kind="Comment")
    await comment_service.delete_comment(
        session,
        tenant_id=tenant_id,
        comment_id=cid,
        actor_id=user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/comments", response_model=list[CommentResponse])
async def list_comments_endpoint(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[CommentResponse]:
    """List comments on a project (internal + shared). All staff can read."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    comments = await comment_service.list_comments(session, tenant_id=tenant_id, project_id=pid)
    return [_to_comment_response(c) for c in comments]
