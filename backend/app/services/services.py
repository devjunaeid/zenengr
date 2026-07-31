"""Service catalog business logic — CRUD for Service + MilestoneStepTemplate."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorType
from app.models.service import Service
from app.repositories import services as service_repo
from app.services.audit import log as audit_log

# ── Exceptions ───────────────────────────────────────────────────────────────


class ServiceNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _normalize_step_inputs(steps: list[Any]) -> list[dict[str, Any]]:
    """Normalize MilestoneStepInput-like values into dicts with renumbered sequence_order.

    Input order is preserved; sequence_order becomes 1, 2, 3, ... regardless of
    submitted values. Duplicate sequence_order after normalization is impossible
    since we always produce 1..N.
    """
    normalized: list[dict[str, Any]] = []
    for idx, step in enumerate(steps, start=1):
        if hasattr(step, "model_dump"):
            data = step.model_dump()
        elif isinstance(step, dict):
            data = dict(step)
        else:
            data = {
                "name": step.name,
                "sequence_order": step.sequence_order,
                "expected_duration_days": step.expected_duration_days,
                "description": step.description,
            }
        data["sequence_order"] = idx
        normalized.append(data)
    return normalized


# ── CRUD ─────────────────────────────────────────────────────────────────────


async def create_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str,
    description: str = "",
    default_price: Decimal | None = None,
    is_active: bool = True,
    steps: list[Any] | None = None,
    actor_id: uuid.UUID,
) -> Service:
    """Create a service with its milestone step templates atomically."""
    service = await service_repo.create_service(
        session,
        tenant_id=tenant_id,
        name=name,
        description=description,
        default_price=default_price,
        is_active=is_active,
    )

    normalized_steps = _normalize_step_inputs(steps or [])
    if normalized_steps:
        await service_repo.replace_milestone_steps(session, service, normalized_steps)

    await session.flush()
    await session.refresh(service, attribute_names=["milestone_steps"])

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="service.created",
        entity_type="service",
        entity_id=str(service.id),
        details={"name": name, "step_count": len(normalized_steps)},
    )

    await session.commit()
    return service


async def get_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Service:
    """Get service scoped to tenant. Raises 404 if not found."""
    service = await service_repo.get_service_for_tenant_with_steps(
        session, tenant_id, service_id
    )
    if service is None:
        raise ServiceNotFoundError()
    return service


async def list_services(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
    q: str | None = None,
    sort: str | None = None,
) -> dict[str, Any]:
    """List services for a tenant. Returns items with computed step_count."""
    items, total = await service_repo.list_services_for_tenant(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
        q=q,
        sort=sort,
    )

    result_items: list[dict[str, Any]] = []
    for s in items:
        result_items.append(
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "default_price": s.default_price,
                "is_active": s.is_active,
                "step_count": len(s.milestone_steps),
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
        )

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_service_detail(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Service:
    """Get a service with steps eager-loaded. Raises 404 if not found."""
    return await get_service(session, tenant_id=tenant_id, service_id=service_id)


async def update_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    updates: dict[str, Any],
    actor_id: uuid.UUID,
) -> Service:
    """Update service fields. If `steps` provided, atomically replace the full set."""
    service = await service_repo.get_service_for_tenant(session, tenant_id, service_id)
    if service is None:
        raise ServiceNotFoundError()

    # Separate scalar updates from steps
    steps_payload = updates.pop("steps", None)

    changed_keys: list[str] = []
    for key, val in updates.items():
        old_val = getattr(service, key, None)
        if old_val != val:
            changed_keys.append(key)
            setattr(service, key, val)

    if steps_payload is not None:
        normalized = _normalize_step_inputs(steps_payload)
        await service_repo.replace_milestone_steps(session, service, normalized)
        changed_keys.append("steps")

    if changed_keys:
        await session.flush()
        await session.refresh(service, attribute_names=["milestone_steps"])

        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="service.updated",
            entity_type="service",
            entity_id=str(service.id),
            details={"changed_keys": changed_keys},
        )

        await session.commit()

    return service


async def delete_service(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    service_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    """Hard-delete a service. FK CASCADE removes milestone_step_templates."""
    service = await service_repo.get_service_for_tenant(session, tenant_id, service_id)
    if service is None:
        raise ServiceNotFoundError()

    await service_repo.delete_service(session, service)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="service.deleted",
        entity_type="service",
        entity_id=str(service_id),
    )

    await session.commit()
