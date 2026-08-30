"""Project management business logic (FEAT-007, US-025..US-027).

Owns the orchestration of:
- Project creation with service attachment + milestone instantiation
- Project detail / list (with rollups)
- Project status / metadata updates
- Mid-project service attachment (active projects only)
- Milestone updates
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.enums import (
    ActorType,
    MilestoneStatus,
    ProjectMemberRole,
    ProjectServiceStatus,
    ProjectStatus,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.milestone_step_template import MilestoneStepTemplate
from app.models.project import Project, ProjectMember
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService
from app.models.service import Service
from app.repositories import clients as client_repo
from app.repositories import projects as project_repo
from app.repositories import services as service_repo
from app.services import financials as financials_service
from app.services import ledger as ledger_service
from app.services.audit import log as audit_log
from app.services.notifications import (
    notify_milestone_completed,
    notify_project_created,
    safe_notify,
)

logger = logging.getLogger(__name__)

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


class ProjectServiceAlreadyCancelledError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project service already cancelled",
        )


# ── Helpers ────────────────────────────────────────────────────────────────


async def _get_client(session: AsyncSession, tenant_id: uuid.UUID, client_id: uuid.UUID) -> Client:
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


async def _get_admin_user(session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> bool:
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
    actor_id: uuid.UUID | None,
    price: Decimal | None = None,
) -> ProjectService:
    """Create ProjectService + instantiate milestone rows from templates.

    Cumulative planned_date = start_date + sum(prior expected_duration_days)
    if both start_date and prior durations exist; else None for that step.

    Also writes the FEAT-018 charge LedgerEntry (FR-18.5): amount = price at
    attachment (explicit override, else service.default_price), entry_date =
    today, description = service name.
    """
    price_at_attachment = price if price is not None else service.default_price
    project_service = await project_repo.attach_service(
        session,
        project,
        service,
        price_at_attachment=price_at_attachment,
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
            planned = _compute_planned_date(start_date, prior_days + tmpl.expected_duration_days)
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

    await ledger_service.add_service_charge(
        session,
        project_id=project.id,
        project_service_id=project_service.id,
        amount=(
            project_service.price_at_attachment
            if project_service.price_at_attachment is not None
            else Decimal("0")
        ),
        description=service.name,
        actor_id=actor_id,
    )
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
    service_prices: dict[uuid.UUID, Decimal] | None = None,
    auto_invoice: bool = False,
    actor_id: uuid.UUID,
) -> Project:
    """Create a project in Draft + attach services + instantiate milestones.

    With auto_invoice=True (and services selected), one DRAFT invoice is
    created after the project commit carrying every attached service as a
    snapshot line item (quantity 1, unit_price = price_at_attachment,
    description = service name, entry_date = today). Discounts are
    intentionally NOT applied to auto-drafts - the admin edits the draft
    as needed.
    """
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
    project.auto_invoice = False

    if owner_id is not None:
        owner_member = ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectMemberRole.LEAD,
            tenant_id=tenant_id,
        )
        session.add(owner_member)

    for svc in services:
        override = (service_prices or {}).get(svc.id)
        await _attach_service_internal(
            session,
            project,
            svc,
            start_date=start_date,
            actor_id=actor_id,
            price=override,
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
    await safe_notify(notify_project_created(session, project_id=project.id))
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


async def get_project_overview(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Build project overview data: milestone completion + financial summary.

    404 if project not found in tenant. Financial fields come from
    services/financials.py (live sums; see TODO-095/FEAT-008).
    """
    project = await get_project(session, tenant_id=tenant_id, project_id=project_id)
    total = len(project.milestones)
    completed = sum(1 for m in project.milestones if m.status == MilestoneStatus.COMPLETED)
    pct = 0.0 if total == 0 else round(completed / total * 100, 2)
    financials = await financials_service.get_project_financials(session, project_id=project.id)
    invoices = await financials_service.list_linked_invoices(session, project_id=project.id)
    service_breakdown = await financials_service.get_project_financials_by_service(
        session, project_id=project.id
    )
    return {
        "project_id": project.id,
        "name": project.name,
        "status": project.status,
        "milestone_total": total,
        "milestone_completed": completed,
        "milestone_completion_pct": pct,
        "financials": financials,
        "invoices": invoices,
        "service_breakdown": service_breakdown,
    }


async def list_projects(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: ProjectStatus | None = None,
    client_id: uuid.UUID | None = None,
    q: str | None = None,
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
        q=q,
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
                "auto_invoice": p.auto_invoice,
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

    if "owner_id" in updates and updates["owner_id"] is not None:
        new_owner_id = updates["owner_id"]
        stmt = select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.user_id == new_owner_id,
        )
        existing_m = (await session.execute(stmt)).scalar_one_or_none()
        if existing_m is None:
            session.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=new_owner_id,
                    role=ProjectMemberRole.LEAD,
                    tenant_id=tenant_id,
                )
            )
        else:
            existing_m.role = ProjectMemberRole.LEAD

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


async def _reload_with_relations(session: AsyncSession, project: Project) -> Project:
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
    price: Decimal | None = None,
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
        session,
        project,
        service,
        start_date=project.start_date,
        actor_id=actor_id,
        price=price,
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

    # AUTO-INVOICE (opt-in): append this service to the project's open draft
    # Wire the relationship in-memory: async SQLAlchemy cannot lazy-load
    # relationships outside the greenlet, and attach_service_endpoint reads
    # project_service.service.name right after this returns. The object is
    # already in the identity map (expire_on_commit=False), so no IO occurs.
    project_service.service = service
    return project_service, milestone_count


# ── Remove project service (TODO-070) ──────────────────────────────────────


async def remove_project_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> ProjectService | None:
    """Remove a project service from a project.

    Hard-deletes the project_service (milestones cascade) when no invoice
    line item references it; otherwise soft-cancels it (status=CANCELLED)
    so historical invoices keep their line-item references intact.

    Returns the cancelled ProjectService on the soft path, None on hard delete.
    """
    project = await project_repo.get_project_for_tenant(session, tenant_id, project_id)
    if project is None:
        raise ProjectNotFoundError()

    ps = await project_repo.get_project_service_for_tenant(session, tenant_id, project_service_id)
    if ps is None or ps.project_id != project_id:
        raise ProjectServiceNotAttachedError()

    if ps.status == ProjectServiceStatus.CANCELLED:
        raise ProjectServiceAlreadyCancelledError()

    # Snapshot identity + price + name BEFORE any delete: on the hard path the
    # ProjectService row is gone before we write the ledger reversal.
    ps_id = ps.id
    reversal_amount = ps.price_at_attachment if ps.price_at_attachment is not None else Decimal("0")
    svc = await session.get(Service, ps.service_id)
    svc_name = svc.name if svc is not None else ""

    # Any invoice line item referencing this project service blocks hard delete
    # (the FK would be violated regardless of invoice status).
    li_q = (
        select(InvoiceLineItem.id)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(InvoiceLineItem.project_service_id == project_service_id)
        .limit(1)
    )
    referenced = (await session.execute(li_q)).scalar_one_or_none()

    if referenced is not None:
        await project_repo.cancel_project_service(session, ps)
        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="project.service_cancelled",
            entity_type="project",
            entity_id=str(project.id),
            details={"project_service_id": str(project_service_id)},
        )
        # FEAT-018 offsetting reversal keeps the ledger honest (FR-18.5).
        await ledger_service.add_service_reversal(
            session,
            project_id=project.id,
            project_service_id=ps_id,
            amount=reversal_amount,
            description=f"Service removed: {svc_name}",
            actor_id=actor_id,
        )
        await session.commit()
        return ps

    await project_repo.delete_project_service(session, ps)
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="project.service_removed",
        entity_type="project",
        entity_id=str(project.id),
        details={"project_service_id": str(project_service_id)},
    )
    # FEAT-018 offsetting reversal keeps the ledger honest (FR-18.5).
    await ledger_service.add_service_reversal(
        session,
        project_id=project.id,
        project_service_id=ps_id,
        amount=reversal_amount,
        description=f"Service removed: {svc_name}",
        actor_id=actor_id,
    )
    await session.commit()
    return None


# ── Milestone ops ───────────────────────────────────────────────────────────


async def get_milestone(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    milestone_id: uuid.UUID,
) -> ProjectMilestone:
    milestone = await project_repo.get_milestone_for_tenant(session, tenant_id, milestone_id)
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
    milestone = await project_repo.get_milestone_for_tenant(session, tenant_id, milestone_id)
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
        if milestone.status == MilestoneStatus.COMPLETED:
            await safe_notify(notify_milestone_completed(session, milestone_id=milestone.id))

    return milestone


def serialize_member(m: ProjectMember) -> dict[str, Any]:
    user = getattr(m, "user", None)
    return {
        "id": m.id,
        "project_id": m.project_id,
        "user_id": m.user_id,
        "role": m.role,
        "full_name": user.full_name if user else None,
        "email": user.email if user else None,
        "created_at": m.created_at,
    }


async def list_project_members(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> list[dict[str, Any]]:
    project = await get_project(session, tenant_id=tenant_id, project_id=project_id)
    return [serialize_member(m) for m in project.members]


async def add_project_member(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: ProjectMemberRole,
) -> dict[str, Any]:
    await get_project(session, tenant_id=tenant_id, project_id=project_id)
    if not await _get_admin_user(session, tenant_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found in tenant"
        )

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this project",
        )

    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        tenant_id=tenant_id,
    )
    session.add(member)
    await session.commit()

    stmt = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.id == member.id)
    )
    member = (await session.execute(stmt)).scalar_one()
    return serialize_member(member)


async def update_project_member(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    role: ProjectMemberRole,
) -> dict[str, Any]:
    await get_project(session, tenant_id=tenant_id, project_id=project_id)
    stmt = (
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(
            ProjectMember.id == member_id,
            ProjectMember.project_id == project_id,
            ProjectMember.tenant_id == tenant_id,
        )
    )
    member = (await session.execute(stmt)).scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found"
        )

    member.role = role
    await session.commit()
    await session.refresh(member)
    return serialize_member(member)


async def remove_project_member(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    member_id: uuid.UUID,
) -> None:
    await get_project(session, tenant_id=tenant_id, project_id=project_id)
    stmt = select(ProjectMember).where(
        ProjectMember.id == member_id,
        ProjectMember.project_id == project_id,
        ProjectMember.tenant_id == tenant_id,
    )
    member = (await session.execute(stmt)).scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project member not found"
        )

    await session.delete(member)
    await session.commit()

