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

from sqlalchemy import func, or_, select
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


async def get_project_financials(session: AsyncSession, *, project_id: uuid.UUID) -> dict[str, Any]:
    """Project financial rollup derived directly from the project ledger and project costs.

    Avoids summing duplicate or on-demand invoices, returning exact
    total billed, paid, balance due, total costs, and live profit/loss.
    """
    from app.models.purchase_entry import PurchaseEntry, PurchaseEntryItem
    from app.services.ledger import compute_project_ledger_summary

    summary = await compute_project_ledger_summary(session, project_id=project_id)

    # Cost rollup from purchase entries
    cost_stmt = select(func.coalesce(func.sum(PurchaseEntry.grand_total), 0)).where(
        PurchaseEntry.project_id == project_id
    )
    total_cost_dec = (await session.execute(cost_stmt)).scalar() or Decimal("0")

    total_billed_dec = Decimal(str(summary.get("total") or summary.get("total_billed") or "0"))
    total_paid_dec = Decimal(str(summary.get("paid") or summary.get("total_paid") or "0"))

    gross_profit = total_billed_dec - total_cost_dec
    net_profit = total_paid_dec - total_cost_dec
    profit_margin_pct = (
        round(float(gross_profit / total_billed_dec * 100), 2)
        if total_billed_dec > Decimal("0")
        else 0.0
    )

    # Category breakdown (materials, labour, subcontract, etc.)
    cat_stmt = (
        select(
            PurchaseEntryItem.category,
            func.coalesce(func.sum(PurchaseEntryItem.total), 0),
        )
        .join(PurchaseEntry, PurchaseEntryItem.purchase_entry_id == PurchaseEntry.id)
        .where(PurchaseEntry.project_id == project_id)
        .group_by(PurchaseEntryItem.category)
    )
    cat_rows = (await session.execute(cat_stmt)).all()
    cost_by_category = {cat: f"{amt:.2f}" for cat, amt in cat_rows}

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
        "total_cost": f"{total_cost_dec:.2f}",
        "gross_profit": f"{gross_profit:.2f}",
        "net_profit": f"{net_profit:.2f}",
        "profit_margin_pct": profit_margin_pct,
        "cost_by_category": cost_by_category,
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

    from decimal import ROUND_HALF_UP

    from app.models.enums import (
        DiscountType,
        LedgerEntryType,
        PaymentKind,
        TransactionDirection,
    )
    from app.models.ledger_entry import LedgerEntry
    from app.models.payment import Payment
    from app.models.project_service import ProjectService
    from app.models.transaction import Transaction

    def _m(v: Decimal | int | float) -> Decimal:
        return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    client_billed: dict[uuid.UUID, Decimal] = {cid: Decimal("0") for cid in client_ids}
    client_paid: dict[uuid.UUID, Decimal] = {cid: Decimal("0") for cid in client_ids}

    # ── 1. Fetch all projects for these clients ──────────────────────────────
    proj_stmt = select(Project).where(Project.client_id.in_(client_ids))
    projects = list((await session.execute(proj_stmt)).scalars().all())
    project_ids = [p.id for p in projects]

    if project_ids:
        # ── 2. Bulk fetch non-void ledger charges for all projects ───────────────
        charge_stmt = select(LedgerEntry).where(
            LedgerEntry.project_id.in_(project_ids),
            LedgerEntry.voided_at.is_(None),
        )
        all_charges = list((await session.execute(charge_stmt)).scalars().all())
        charges_by_proj: dict[uuid.UUID, list] = {pid: [] for pid in project_ids}
        for ch in all_charges:
            charges_by_proj[ch.project_id].append(ch)

        # ── 2b. Bulk fetch direct unified payments for projects ──────────────────
        pay_stmt = select(Payment).where(
            Payment.project_id.in_(project_ids),
            Payment.voided_at.is_(None),
        )
        all_pays = list((await session.execute(pay_stmt)).scalars().all())
        pays_by_proj: dict[uuid.UUID, list] = {pid: [] for pid in project_ids}
        for p in all_pays:
            pays_by_proj[p.project_id].append(p)

        # ── 3. Bulk fetch transactions on non-draft / statement invoices ─────────
        tx_stmt = (
            select(Transaction)
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .where(
                Invoice.project_id.in_(project_ids),
                or_(Invoice.status != InvoiceStatus.DRAFT, Invoice.is_auto.is_(True)),
                Invoice.status != InvoiceStatus.VOID,
                Transaction.voided_at.is_(None),
            )
        )
        all_txs = list((await session.execute(tx_stmt)).scalars().all())

        inv_stmt = select(Invoice.id, Invoice.project_id).where(
            Invoice.project_id.in_(project_ids),
            or_(Invoice.status != InvoiceStatus.DRAFT, Invoice.is_auto.is_(True)),
            Invoice.status != InvoiceStatus.VOID,
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

        # ── 4b. Fallback for projects with no LedgerEntry charges ────────────────
        empty_charge_pids = [pid for pid in project_ids if not charges_by_proj.get(pid)]
        ps_fallback_by_proj: dict[uuid.UUID, Decimal] = {}
        if empty_charge_pids:
            ps_stmt = (
                select(
                    ProjectService.project_id,
                    func.coalesce(func.sum(ProjectService.price_at_attachment), 0),
                )
                .where(ProjectService.project_id.in_(empty_charge_pids))
                .group_by(ProjectService.project_id)
            )
            for pid, amt in (await session.execute(ps_stmt)).all():
                ps_fallback_by_proj[pid] = Decimal(amt)

        # ── 5. Aggregate per project → roll up per client ────────────────────────
        for p in projects:
            pid = p.id
            charges = charges_by_proj.get(pid, [])
            direct_pays = pays_by_proj.get(pid, [])
            txs = txs_by_proj.get(pid, [])
            custom_amount = custom_by_proj.get(pid, Decimal("0"))
            ps_fallback = ps_fallback_by_proj.get(pid, Decimal("0"))

            # Subtotal from CHARGE entries + custom lines + fallback
            charge_subtotal = sum(
                (_m(ch.amount) for ch in charges if ch.type == LedgerEntryType.CHARGE),
                Decimal("0"),
            )
            subtotal = _m(charge_subtotal + custom_amount + ps_fallback)

            # Apply project discount
            discount_amount = Decimal("0")
            if subtotal > 0 and p.discount_type is not None and p.discount_value is not None:
                if p.discount_type == DiscountType.PERCENTAGE:
                    discount_amount = _m(subtotal * p.discount_value / Decimal("100"))
                else:
                    discount_amount = min(_m(p.discount_value), subtotal)
            total = _m(subtotal - discount_amount)

            # Payments/refunds from direct Payment table
            payments = Decimal("0")
            refunds = Decimal("0")
            known_payment_ids = set()
            for pay in direct_pays:
                known_payment_ids.add(pay.id)
                if pay.kind == PaymentKind.RECEIPT:
                    payments += _m(pay.amount)
                else:
                    refunds += _m(pay.amount)

            # Payments/refunds from ledger entries (skip mirrored Payments)
            for ch in charges:
                if ch.source_id is not None and ch.source_id in known_payment_ids:
                    continue
                if ch.type == LedgerEntryType.PAYMENT:
                    payments += _m(ch.amount)
                elif ch.type == LedgerEntryType.REFUND:
                    refunds += _m(ch.amount)

            # Supplement with transactions not already accounted for
            known_source_ids = {
                ch.source_id for ch in charges if ch.source_id is not None
            } | known_payment_ids
            for tx in txs:
                if tx.id in known_source_ids or (
                    tx.payment_id is not None and tx.payment_id in known_source_ids
                ):
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

    # ── 6. Standalone client invoices (project_id IS NULL) ───────────────────
    standalone_inv_stmt = (
        select(Invoice)
        .where(
            Invoice.client_id.in_(client_ids),
            Invoice.project_id.is_(None),
            or_(Invoice.status != InvoiceStatus.DRAFT, Invoice.is_auto.is_(True)),
            Invoice.status != InvoiceStatus.VOID,
        )
    )
    standalone_invs = list((await session.execute(standalone_inv_stmt)).scalars().all())
    for sinv in standalone_invs:
        client_billed[sinv.client_id] += _m(sinv.total)

    if standalone_invs:
        sinv_ids = [s.id for s in standalone_invs]
        stx_stmt = (
            select(Transaction, Invoice.client_id)
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .where(
                Invoice.id.in_(sinv_ids),
                Transaction.voided_at.is_(None),
            )
        )
        for stx, scid in (await session.execute(stx_stmt)).all():
            if stx.direction == TransactionDirection.DEBIT:
                client_paid[scid] += _m(stx.amount)
            else:
                client_paid[scid] -= _m(stx.amount)

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
