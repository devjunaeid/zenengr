"""Financial rollup helpers (FEAT-009, TODO-095; FEAT-015).

Computes live totals from the Invoice/Transaction models:
- get_project_financials: per-project invoiced / paid / balance due
- list_linked_invoices: non-draft invoices of a project
- get_client_financials / get_client_financials_batch: per-client rollups
  (batch variant used by the clients list to avoid N+1)
Paid = sum of allocations on the scope's invoices (payments + advance
applications) minus refunds (credit transactions). Void and Draft invoices
are excluded from all money totals.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InvoiceStatus, TransactionDirection
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.project import Project
from app.models.service import Service
from app.models.transaction import PaymentAllocation, Transaction

_MONEY_STATUSES = [
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.PAID,
]


def _fmt(value: Decimal | int | float) -> str:
    """Format a money value as a 2-decimal string; None/missing -> "0.00"."""
    if value is None:
        return "0.00"
    return f"{Decimal(value):.2f}"


def _clamp_non_negative(value: Decimal) -> Decimal:
    return value if value >= Decimal("0") else Decimal("0")


async def get_project_financials(session: AsyncSession, *, project_id: uuid.UUID) -> dict[str, str]:
    """Project financial rollup from live invoice + transaction sums."""
    invoiced_q = select(func.coalesce(func.sum(Invoice.total), 0)).where(
        Invoice.project_id == project_id,
        Invoice.status.in_(_MONEY_STATUSES),
    )
    invoiced = Decimal((await session.execute(invoiced_q)).scalar_one())

    paid_q = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.project_id == project_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
    )
    paid_allocations = Decimal((await session.execute(paid_q)).scalar_one())

    refund_q = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.project_id == project_id,
            Invoice.status.in_(_MONEY_STATUSES),
            Transaction.direction == TransactionDirection.CREDIT,
        )
    )
    refunds = Decimal((await session.execute(refund_q)).scalar_one())
    paid = _clamp_non_negative(paid_allocations - refunds)

    balance = _clamp_non_negative(invoiced - paid)
    return {
        "total_invoiced": _fmt(invoiced),
        "total_paid": _fmt(paid),
        "balance_due": _fmt(balance),
    }


async def get_project_financials_by_service(
    session: AsyncSession, *, project_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Per-service invoiced / paid / outstanding for a project's money invoices.

    Line items with a NULL service_id (custom lines) are labeled "Custom".
    Returns rows ordered by service name.
    """
    invoiced_rows = (
        await session.execute(
            select(
                InvoiceLineItem.service_id,
                Service.name,
                func.coalesce(func.sum(InvoiceLineItem.amount), 0),
            )
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .outerjoin(Service, Service.id == InvoiceLineItem.service_id)
            .where(
                Invoice.project_id == project_id,
                Invoice.status.in_(_MONEY_STATUSES),
            )
            .group_by(InvoiceLineItem.service_id, Service.name)
        )
    ).all()

    paid_rows = (
        await session.execute(
            select(
                InvoiceLineItem.service_id,
                func.coalesce(func.sum(PaymentAllocation.amount), 0),
            )
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .join(PaymentAllocation, PaymentAllocation.line_item_id == InvoiceLineItem.id)
            .where(
                Invoice.project_id == project_id,
                Invoice.status.in_(_MONEY_STATUSES),
            )
            .group_by(InvoiceLineItem.service_id)
        )
    ).all()

    invoiced_map: dict[uuid.UUID | None, Decimal] = {}
    name_map: dict[uuid.UUID | None, str] = {}
    for service_id, name, amount in invoiced_rows:
        sid: uuid.UUID | None = service_id
        invoiced_map[sid] = Decimal(amount)
        name_map[sid] = name if name else "Custom"

    paid_map: dict[uuid.UUID | None, Decimal] = {
        service_id: Decimal(amount) for service_id, amount in paid_rows
    }

    items: list[dict[str, Any]] = []
    for sid in set(invoiced_map) | set(paid_map):
        invoiced = invoiced_map.get(sid, Decimal("0"))
        paid = paid_map.get(sid, Decimal("0"))
        outstanding = _clamp_non_negative(invoiced - paid)
        items.append(
            {
                "service_id": sid,
                "service_name": name_map.get(sid, "Custom"),
                "total_invoiced": _fmt(invoiced),
                "total_paid": _fmt(paid),
                "total_outstanding": _fmt(outstanding),
            }
        )
    items.sort(key=lambda item: item["service_name"].lower())
    return items


async def list_linked_invoices(
    session: AsyncSession, *, project_id: uuid.UUID
) -> list[dict[str, Any]]:
    """All non-draft invoices of a project, newest first."""
    stmt = (
        select(Invoice)
        .where(
            Invoice.project_id == project_id,
            Invoice.status != InvoiceStatus.DRAFT,
        )
        .order_by(Invoice.created_at.desc())
    )
    result = await session.execute(stmt)
    invoices = list(result.scalars().all())
    return [
        {
            "id": inv.id,
            "number": inv.invoice_number or "",
            "status": inv.status.value,
            "total": f"{inv.total:.2f}",
        }
        for inv in invoices
    ]


async def get_client_financials(session: AsyncSession, *, client_id: uuid.UUID) -> dict[str, str]:
    """Client financial rollup across all of the client's projects."""
    invoiced = await _client_invoiced(session, client_id)
    paid = await _client_paid(session, client_id)
    outstanding = _clamp_non_negative(invoiced - paid)
    return {
        "total_invoiced": _fmt(invoiced),
        "total_paid": _fmt(paid),
        "total_outstanding": _fmt(outstanding),
    }


async def get_client_financials_batch(
    session: AsyncSession, *, client_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, str]]:
    """Per-client financial rollups in one grouped query per total."""
    result: dict[uuid.UUID, dict[str, str]] = {}
    if not client_ids:
        return result

    invoiced_rows = (
        await session.execute(
            select(Project.client_id, func.coalesce(func.sum(Invoice.total), 0))
            .join(Invoice, Invoice.project_id == Project.id)
            .where(
                Project.client_id.in_(client_ids),
                Invoice.status.in_(_MONEY_STATUSES),
            )
            .group_by(Project.client_id)
        )
    ).all()
    paid_rows = (
        await session.execute(
            select(Project.client_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .join(Project, Invoice.project_id == Project.id)
            .where(
                Project.client_id.in_(client_ids),
                Invoice.status.in_(_MONEY_STATUSES),
            )
            .group_by(Project.client_id)
        )
    ).all()
    refund_rows = (
        await session.execute(
            select(Project.client_id, func.coalesce(func.sum(Transaction.amount), 0))
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .join(Project, Invoice.project_id == Project.id)
            .where(
                Project.client_id.in_(client_ids),
                Invoice.status.in_(_MONEY_STATUSES),
                Transaction.direction == TransactionDirection.CREDIT,
            )
            .group_by(Project.client_id)
        )
    ).all()

    invoiced_map = {client_id: Decimal(amount) for client_id, amount in invoiced_rows}
    refund_rows_map = {client_id: Decimal(amount) for client_id, amount in refund_rows}
    paid_map = {
        client_id: _clamp_non_negative(
            Decimal(alloc) - refund_rows_map.get(client_id, Decimal("0"))
        )
        for client_id, alloc in paid_rows
    }
    for cid in client_ids:
        invoiced = invoiced_map.get(cid, Decimal("0"))
        paid = paid_map.get(cid, Decimal("0"))
        outstanding = _clamp_non_negative(invoiced - paid)
        result[cid] = {
            "total_invoiced": _fmt(invoiced),
            "total_paid": _fmt(paid),
            "total_outstanding": _fmt(outstanding),
        }
    return result


async def _client_invoiced(session: AsyncSession, client_id: uuid.UUID) -> Decimal:
    stmt = (
        select(func.coalesce(func.sum(Invoice.total), 0))
        .join(Project, Invoice.project_id == Project.id)
        .where(
            Project.client_id == client_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
    )
    return Decimal((await session.execute(stmt)).scalar_one())


async def _client_paid(session: AsyncSession, client_id: uuid.UUID) -> Decimal:
    alloc_stmt = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .join(Project, Invoice.project_id == Project.id)
        .where(
            Project.client_id == client_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
    )
    allocations = Decimal((await session.execute(alloc_stmt)).scalar_one())

    refund_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .join(Project, Invoice.project_id == Project.id)
        .where(
            Project.client_id == client_id,
            Invoice.status.in_(_MONEY_STATUSES),
            Transaction.direction == TransactionDirection.CREDIT,
        )
    )
    refunds = Decimal((await session.execute(refund_stmt)).scalar_one())
    return _clamp_non_negative(allocations - refunds)
