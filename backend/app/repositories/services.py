"""Service repository -- thin data access layer for Service + MilestoneStepTemplate."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.milestone_step_template import MilestoneStepTemplate
from app.models.project_service import ProjectService
from app.models.service import Service


async def get_service(session: AsyncSession, service_id: uuid.UUID) -> Service | None:
    """Fetch service by primary key (no tenant scope)."""
    stmt = select(Service).where(Service.id == service_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_service_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Service | None:
    """Fetch service by id scoped to a tenant. None if not found or wrong tenant."""
    stmt = select(Service).where(Service.id == service_id, Service.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_service_with_steps(
    session: AsyncSession,
    service_id: uuid.UUID,
) -> Service | None:
    """Fetch service by id with milestone_steps eager-loaded."""
    stmt = (
        select(Service)
        .options(selectinload(Service.milestone_steps))
        .where(Service.id == service_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def get_service_for_tenant_with_steps(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Service | None:
    """Fetch service by id scoped to tenant with milestone_steps eager-loaded."""
    stmt = (
        select(Service)
        .options(selectinload(Service.milestone_steps))
        .where(Service.id == service_id, Service.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def count_project_services(session: AsyncSession, service_id: uuid.UUID) -> int:
    """Count ProjectService rows referencing a service (TODO-060).

    A service is "in use" when at least one project has it attached, so the
    count spans the whole tenant (service ids are globally unique).
    """
    stmt = (
        select(func.count())
        .select_from(ProjectService)
        .where(ProjectService.service_id == service_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    description: str = "",
    default_price: Decimal | None = None,
    is_active: bool = True,
) -> Service:
    """Create a new service. Caller is responsible for adding milestone_steps."""
    service = Service(
        tenant_id=tenant_id,
        name=name,
        description=description,
        default_price=default_price,
        is_active=is_active,
    )
    session.add(service)
    await session.flush()
    await session.refresh(service)
    return service


async def list_services_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> tuple[list[Service], int]:
    """List services for a tenant with filtering, search, sort, pagination."""
    conditions = [Service.tenant_id == tenant_id]
    if is_active is not None:
        conditions.append(Service.is_active == is_active)
    if q:
        conditions.append(Service.name.ilike(f"%{q}%"))

    query = select(Service).options(selectinload(Service.milestone_steps)).where(*conditions)

    # Count (strip options for count subquery)
    count_q = select(func.count()).select_from(select(Service).where(*conditions).subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    # Sort
    if sort:
        desc = sort.startswith("-")
        col_name = sort.lstrip("-")
        col = getattr(Service, col_name, None)
        if col is not None:
            query = query.order_by(col.desc() if desc else col.asc())
        else:
            query = query.order_by(Service.name.asc())
    else:
        query = query.order_by(Service.name.asc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    items = list(result.scalars().all())

    return items, total


async def update_service(
    session: AsyncSession,
    service: Service,
    **kwargs: Any,
) -> Service:
    """Update service fields. Caller must flush."""
    for key, val in kwargs.items():
        setattr(service, key, val)
    await session.flush()
    await session.refresh(service)
    return service


async def delete_service(session: AsyncSession, service: Service) -> None:
    """Hard-delete a service. FK CASCADE removes milestone_step_templates."""
    await session.delete(service)
    await session.flush()


async def replace_milestone_steps(
    session: AsyncSession,
    service: Service,
    steps: list[dict[str, Any]],
) -> None:
    """Atomically replace the full set of milestone step templates for a service.

    Existing step templates are deleted and the new ordered list is inserted.
    `steps` is a list of dicts with keys: name, sequence_order,
    expected_duration_days (optional), description (optional).
    """
    # Delete existing via direct query (avoids lazy-load on a fresh service)
    from sqlalchemy import delete as sql_delete

    await session.execute(
        sql_delete(MilestoneStepTemplate).where(MilestoneStepTemplate.service_id == service.id)
    )

    # Insert new
    for step_data in steps:
        step = MilestoneStepTemplate(
            service_id=service.id,
            name=step_data["name"],
            sequence_order=step_data["sequence_order"],
            expected_duration_days=step_data.get("expected_duration_days"),
            description=step_data.get("description", ""),
        )
        session.add(step)

    if steps:
        await session.flush()
