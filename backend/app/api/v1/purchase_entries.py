"""Purchase entry API endpoints (standalone module, no invoice link).

Base path: /api/v1/tenant/projects/{project_id}/purchase-entries
Guards: admin+manager for writes; all staff can read.
"""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.project import Project
from app.models.purchase_entry import PurchaseEntry, PurchaseEntryItem
from app.schemas.purchase_entries import (
    PurchaseEntryCreateRequest,
    PurchaseEntryItemResponse,
    PurchaseEntryListItem,
    PurchaseEntryListResponse,
    PurchaseEntryResponse,
    PurchaseEntryUpdateRequest,
)

router = APIRouter(
    prefix="/tenant/projects/{project_id}/purchase-entries",
    tags=["purchase-entries"],
)

_TWO = Decimal("0.01")


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


async def _get_project(
    session: AsyncSession, tenant_id: uuid.UUID, project_id: uuid.UUID
) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def _get_entry(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    entry_id: uuid.UUID,
) -> PurchaseEntry:
    stmt = (
        select(PurchaseEntry)
        .where(
            PurchaseEntry.id == entry_id,
            PurchaseEntry.project_id == project_id,
            PurchaseEntry.tenant_id == tenant_id,
        )
        .options(selectinload(PurchaseEntry.items))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Purchase entry not found",
        )
    return entry


def _item_to_response(item: PurchaseEntryItem) -> PurchaseEntryItemResponse:
    return PurchaseEntryItemResponse(
        id=item.id,
        item_date=item.item_date,
        description=item.description,
        quantity=f"{item.quantity:.2f}",
        rate=f"{item.rate:.2f}",
        total=f"{item.total:.2f}",
    )


def _entry_to_response(entry: PurchaseEntry) -> PurchaseEntryResponse:
    items = sorted(entry.items, key=lambda i: i.created_at)
    return PurchaseEntryResponse(
        id=entry.id,
        project_id=entry.project_id,
        title=entry.title,
        notes=entry.notes,
        entry_date=entry.entry_date,
        grand_total=f"{entry.grand_total:.2f}",
        created_by_id=entry.created_by_id,
        items=[_item_to_response(i) for i in items],
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _compute_total(quantity: Decimal, rate: Decimal) -> Decimal:
    return (quantity * rate).quantize(_TWO, rounding=ROUND_HALF_UP)


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=PurchaseEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase_entry(
    project_id: str,
    body: PurchaseEntryCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PurchaseEntryResponse:
    """Create a purchase entry with line items. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    await _get_project(session, tenant_id, pid)

    entry = PurchaseEntry(
        tenant_id=tenant_id,
        project_id=pid,
        title=body.title or "",
        notes=body.notes or "",
        entry_date=body.entry_date,
        grand_total=Decimal("0"),
        created_by_id=user.id,
    )
    session.add(entry)
    await session.flush()  # get entry.id

    grand = Decimal("0")
    for row in body.items:
        total = _compute_total(row.quantity, row.rate)
        item = PurchaseEntryItem(
            purchase_entry_id=entry.id,
            item_date=row.item_date,
            description=row.description,
            quantity=row.quantity,
            rate=row.rate,
            total=total,
        )
        session.add(item)
        grand += total

    entry.grand_total = grand.quantize(_TWO, rounding=ROUND_HALF_UP)
    await session.commit()
    await session.refresh(entry)
    # re-load items
    stmt = (
        select(PurchaseEntry)
        .where(PurchaseEntry.id == entry.id)
        .options(selectinload(PurchaseEntry.items))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one()
    return _entry_to_response(entry)


@router.get("/", response_model=PurchaseEntryListResponse)
async def list_purchase_entries(
    project_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> PurchaseEntryListResponse:
    """List purchase entries for a project. All staff can read."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    await _get_project(session, tenant_id, pid)

    count_stmt = select(func.count()).where(
        PurchaseEntry.project_id == pid,
        PurchaseEntry.tenant_id == tenant_id,
    )
    total: int = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        select(PurchaseEntry)
        .where(
            PurchaseEntry.project_id == pid,
            PurchaseEntry.tenant_id == tenant_id,
        )
        .order_by(PurchaseEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).scalars().all()

    # fetch item counts in one query
    ids = [r.id for r in rows]
    counts: dict[uuid.UUID, int] = {}
    if ids:
        count_items_stmt = (
            select(PurchaseEntryItem.purchase_entry_id, func.count())
            .where(PurchaseEntryItem.purchase_entry_id.in_(ids))
            .group_by(PurchaseEntryItem.purchase_entry_id)
        )
        for eid, cnt in (await session.execute(count_items_stmt)).all():
            counts[eid] = cnt

    items = [
        PurchaseEntryListItem(
            id=r.id,
            project_id=r.project_id,
            title=r.title,
            entry_date=r.entry_date,
            grand_total=f"{r.grand_total:.2f}",
            item_count=counts.get(r.id, 0),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return PurchaseEntryListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.get("/{entry_id}", response_model=PurchaseEntryResponse)
async def get_purchase_entry(
    project_id: str,
    entry_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> PurchaseEntryResponse:
    """Get a single purchase entry with its items. All staff can read."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    eid = _parse_uuid(entry_id, kind="PurchaseEntry")
    entry = await _get_entry(session, tenant_id, pid, eid)
    return _entry_to_response(entry)


@router.patch("/{entry_id}", response_model=PurchaseEntryResponse)
async def update_purchase_entry(
    project_id: str,
    entry_id: str,
    body: PurchaseEntryUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PurchaseEntryResponse:
    """Replace header fields and/or all items. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    eid = _parse_uuid(entry_id, kind="PurchaseEntry")
    entry = await _get_entry(session, tenant_id, pid, eid)

    if body.title is not None:
        entry.title = body.title
    if body.notes is not None:
        entry.notes = body.notes
    if body.entry_date is not None:
        entry.entry_date = body.entry_date

    if body.items is not None:
        # full replacement: delete existing, insert new
        for existing in list(entry.items):
            await session.delete(existing)
        await session.flush()

        grand = Decimal("0")
        for row in body.items:
            qty = row.quantity if row.quantity is not None else Decimal("1")
            rate = row.rate if row.rate is not None else Decimal("0")
            desc = row.description or ""
            total = _compute_total(qty, rate)
            item = PurchaseEntryItem(
                purchase_entry_id=entry.id,
                item_date=row.item_date,
                description=desc,
                quantity=qty,
                rate=rate,
                total=total,
            )
            session.add(item)
            grand += total
        entry.grand_total = grand.quantize(_TWO, rounding=ROUND_HALF_UP)

    await session.commit()

    stmt = (
        select(PurchaseEntry)
        .where(PurchaseEntry.id == entry.id)
        .options(selectinload(PurchaseEntry.items))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one()
    return _entry_to_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_entry(
    project_id: str,
    entry_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> Response:
    """Delete a purchase entry. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    eid = _parse_uuid(entry_id, kind="PurchaseEntry")
    entry = await _get_entry(session, tenant_id, pid, eid)
    await session.delete(entry)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
