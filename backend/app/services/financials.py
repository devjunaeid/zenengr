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

from app.models.enums import InvoiceStatus
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.project import Project
from app.models.service import Service
from app.models.transaction import PaymentAllocation

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
    """Project financial rollup derived directly from the project ledger.

    Avoids summing duplicate or on-demand invoices, returning exact
    total billed, paid, and balance due.
    """
    from app.services.ledger import compute_project_ledger_summary

    summary = await compute_project_ledger_summary(session, project_id=project_id)
    return {
        "total_billed": summary["total_billed"],
        "total_paid": summary["total_paid"],
        "balance_due": summary["balance_due"],
        "total": summary["total"],
        "paid": summary["paid"],
        "due": summary["due"],
        "total_invoiced": summary["total_invoiced"],
        "total_outstanding": summary["total_outstanding"],
        "advance_balance": summary["advance_balance"],
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
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    exclude_auto: bool = False,
) -> list[dict[str, Any]]:
    """All non-draft invoices of a project, newest first.

    exclude_auto=True drops auto-generated (statement) invoices, e.g. for
    client-facing views; staff views keep them by default.
    """
    stmt = (
        select(Invoice)
        .where(
            Invoice.project_id == project_id,
            Invoice.status != InvoiceStatus.DRAFT,
        )
        .order_by(Invoice.created_at.desc())
    )
    if exclude_auto:
        stmt = stmt.where(Invoice.is_auto == False)  # noqa: E712
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


async def get_client_financials_batch(
    session: AsyncSession, *, client_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, str]]:
    """Per-client financial rollups via bulk queries (no N+1).

    Runs 4 queries across all projects for the given clients instead of
    calling compute_project_ledger_summary per project, which caused
    asyncpg connection exhaustion under load.
    """
    result: dict[uuid.UUID, dict[str, str]] = {}
    if not client_ids:
        return result

    from app.models.enums import DiscountType, LedgerEntryType, TransactionDirection
    from app.models.ledger_entry import LedgerEntry
    from app.models.transaction import Transaction

    # ── 1. Fetch all projects for these clients ──────────────────────────────
    proj_stmt = select(Project).where(Project.client_id.in_(client_ids))
    projects = list((await session.execute(proj_stmt)).scalars().all())

    if not projects:
        for cid in client_ids:
            result[cid] = {
                "total_billed": "0.00",
                "total_paid": "0.00",
                "total_due": "0.00",
                "total_invoiced": "0.00",
                "total_outstanding": "0.00",
            }
        return result

    project_ids = [p.id for p in projects]

    # ── 2. Bulk fetch ledger charges for all projects ────────────────────────
    charge_stmt = select(LedgerEntry).where(LedgerEntry.project_id.in_(project_ids))
    all_charges = list((await session.execute(charge_stmt)).scalars().all())
    charges_by_proj: dict[uuid.UUID, list] = {pid: [] for pid in project_ids}
    for ch in all_charges:
        charges_by_proj[ch.project_id].append(ch)

    # ── 3. Bulk fetch transactions on non-draft invoices ─────────────────────
    tx_stmt = (
        select(Transaction)
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.project_id.in_(project_ids),
            Invoice.status != InvoiceStatus.DRAFT,
        )
    )
    all_txs = list((await session.execute(tx_stmt)).scalars().all())

    # Need project_id per transaction — fetch via invoice map
    inv_stmt = select(Invoice.id, Invoice.project_id).where(
        Invoice.project_id.in_(project_ids),
        Invoice.status != InvoiceStatus.DRAFT,
    )
    inv_proj_map: dict[uuid.UUID, uuid.UUID] = {}
    for inv_id, proj_id in (await session.execute(inv_stmt)).all():
        inv_proj_map[inv_id] = proj_id

    txs_by_proj: dict[uuid.UUID, list] = {pid: [] for pid in project_ids}
    for tx in all_txs:
        pid = inv_proj_map.get(tx.invoice_id)
        if pid is not None:
            txs_by_proj[pid].append(tx)

    # ── 4. Bulk fetch custom line-item amounts (non-auto invoices) ───────────
    custom_stmt = (
        select(Invoice.project_id, func.coalesce(func.sum(InvoiceLineItem.amount), 0))
        .join(InvoiceLineItem, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.project_id.in_(project_ids),
            Invoice.status != InvoiceStatus.DRAFT,
            Invoice.is_auto.is_(False),
            InvoiceLineItem.project_service_id.is_(None),
        )
        .group_by(Invoice.project_id)
    )
    custom_by_proj: dict[uuid.UUID, Decimal] = {}
    for proj_id, amt in (await session.execute(custom_stmt)).all():
        custom_by_proj[proj_id] = Decimal(amt)

    # ── 5. Aggregate per project → roll up per client ────────────────────────
    from decimal import ROUND_HALF_UP

    def _m(v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    client_billed: dict[uuid.UUID, Decimal] = {cid: Decimal("0") for cid in client_ids}
    client_paid: dict[uuid.UUID, Decimal] = {cid: Decimal("0") for cid in client_ids}

    for p in projects:
        pid = p.id
        charges = charges_by_proj.get(pid, [])
        txs = txs_by_proj.get(pid, [])
        custom_amount = custom_by_proj.get(pid, Decimal("0"))

        # Subtotal from CHARGE entries + custom lines
        charge_subtotal = sum(
            (_m(ch.amount) for ch in charges if ch.type == LedgerEntryType.CHARGE),
            Decimal("0"),
        )
        subtotal = _m(charge_subtotal + custom_amount)

        # Apply project discount
        discount_amount = Decimal("0")
        if subtotal > 0 and p.discount_type is not None and p.discount_value is not None:
            if p.discount_type == DiscountType.PERCENTAGE:
                discount_amount = _m(subtotal * p.discount_value / Decimal("100"))
            else:
                discount_amount = min(_m(p.discount_value), subtotal)
        total = _m(subtotal - discount_amount)

        # Payments/refunds from ledger entries
        payments = sum(
            (_m(ch.amount) for ch in charges if ch.type == LedgerEntryType.PAYMENT),
            Decimal("0"),
        )
        refunds = sum(
            (_m(ch.amount) for ch in charges if ch.type == LedgerEntryType.REFUND),
            Decimal("0"),
        )

        # Supplement with transactions not already in ledger
        known_tx_ids = {ch.source_id for ch in charges if ch.source_id is not None}
        for tx in txs:
            if tx.id in known_tx_ids:
                continue
            if tx.reference_note and "synced" in tx.reference_note.lower():
                continue
            if tx.direction == TransactionDirection.DEBIT:
                payments += _m(tx.amount)
            else:
                refunds += _m(tx.amount)

        paid = _m(payments - refunds)
        client_billed[p.client_id] += total
        client_paid[p.client_id] += paid

    for cid in client_ids:
        billed = client_billed.get(cid, Decimal("0"))
        paid = client_paid.get(cid, Decimal("0"))
        due = _clamp_non_negative(billed - paid)
        result[cid] = {
            "total_billed": _fmt(billed),
            "total_paid": _fmt(paid),
            "total_due": _fmt(due),
            "total_invoiced": _fmt(billed),
            "total_outstanding": _fmt(due),
        }
    return result



async def get_client_financials(session: AsyncSession, *, client_id: uuid.UUID) -> dict[str, str]:
    """Client financial rollup across all of the client's projects from the ledger."""
    batch = await get_client_financials_batch(session, client_ids=[client_id])
    return batch.get(
        client_id,
        {
            "total_billed": "0.00",
            "total_paid": "0.00",
            "total_due": "0.00",
            "total_invoiced": "0.00",
            "total_outstanding": "0.00",
        },
    )
