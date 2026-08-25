"""Invoice transaction business logic (FEAT-009, TODO-089/090/092/093/094; FEAT-015).

Owns the orchestration of:
- Recording a payment against an issued/partially-paid invoice
- Auto proportional allocation of a payment across line items (TODO-094)
- Manual allocation override validation
- Invoice status recompute after payment (PARTIALLY_PAID / PAID)
- Refunds (credit transactions) and advance balances from payment overages
- Manual advance application to other invoices of the same scope (FEAT-015)
- Client ledger building (staff + client portal)

Money is Decimal internally; responses format as 2-decimal strings.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.advance import Advance
from app.models.enums import ActorType, InvoiceStatus, PaymentMethod, TransactionDirection
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.project import Project
from app.models.transaction import PaymentAllocation, Transaction
from app.services.audit import log as audit_log
from app.services.notifications import (
    notify_advance_applied,
    notify_payment_recorded,
    notify_refund_recorded,
    safe_notify,
)

# ── Exceptions ──────────────────────────────────────────────────────────────


class TransactionInvoiceNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )


class TransactionNotPayableError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only issued or partially paid invoices accept payments",
        )


class TransactionAlreadyPaidError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invoice already fully paid",
        )


class TransactionInvalidAllocationError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Allocation line item does not belong to this invoice",
        )


class TransactionAllocationSumError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Allocations must sum to the payment amount",
        )


class TransactionInvalidAmountError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Payment amount must be positive",
        )


class RefundExceedsPaidError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Refund exceeds paid amount",
        )


class ApplyAdvanceError(HTTPException):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail or "Only issued or partially paid invoices accept advance application",
        )


class AdvanceUnavailableError(HTTPException):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail or "No advance balance available",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────


def _money(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_invoice_with_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Fetch an invoice with line_items + project eager-loaded, tenant-scoped."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.project))
        .execution_options(populate_existing=True)
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def _invoice_net_paid(session: AsyncSession, *, invoice_id: uuid.UUID) -> Decimal:
    """Net amount paid against an invoice.

    paid = sum of allocations on the invoice's line items (payment + advance
    applications) minus refunds (credit transactions, which carry no
    allocations).
    """
    paid_q = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .where(InvoiceLineItem.invoice_id == invoice_id)
    )
    paid = Decimal((await session.execute(paid_q)).scalar_one())

    credit_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.invoice_id == invoice_id,
        Transaction.direction == TransactionDirection.CREDIT,
    )
    credits = Decimal((await session.execute(credit_q)).scalar_one())

    return _money(paid - credits)


async def _auto_allocate(invoice: Invoice, amount: Decimal) -> list[dict[str, Any]]:
    """Proportionally split a payment across line items (largest remainder).

    Cents math: each item gets floor(amount_cents * li_cents / total_cents);
    leftover cents go one-per-item to the items with the largest fractional
    part. Zero-total or empty invoices fall back to the first line item.
    """
    line_items = sorted(invoice.line_items, key=lambda li: li.created_at)
    if not line_items:
        return []
    total_cents = int(_money(invoice.total) * 100)
    amount_cents = int(_money(amount) * 100)
    if total_cents <= 0:
        return [{"line_item_id": line_items[0].id, "amount": _money(amount)}]

    shares: list[dict[str, Any]] = []
    for li in line_items:
        li_cents = int(_money(li.amount) * 100)
        shares.append(
            {
                "line_item_id": li.id,
                "amount": (amount_cents * li_cents) // total_cents,
                "frac": (amount_cents * li_cents) % total_cents,
            }
        )

    remainder = amount_cents - sum(s["amount"] for s in shares)
    for s in sorted(shares, key=lambda s: s["frac"], reverse=True):
        if remainder <= 0:
            break
        s["amount"] += 1
        remainder -= 1

    return [
        {
            "line_item_id": s["line_item_id"],
            "amount": _money(Decimal(s["amount"]) / Decimal("100")),
        }
        for s in shares
    ]


async def _validate_allocations(
    invoice: Invoice,
    amount: Decimal,
    allocations: list[Any],
) -> list[dict[str, Any]]:
    """Validate manual allocation override: membership + sum == amount."""
    line_item_ids = {li.id for li in invoice.line_items}
    total = Decimal("0")
    result: list[dict[str, Any]] = []
    for alloc in allocations:
        if alloc.line_item_id not in line_item_ids:
            raise TransactionInvalidAllocationError()
        alloc_amount = _money(alloc.amount)
        result.append({"line_item_id": alloc.line_item_id, "amount": alloc_amount})
        total += alloc_amount
    if _money(total) != _money(amount):
        raise TransactionAllocationSumError()
    return result


async def _recompute_invoice_status(session: AsyncSession, invoice: Invoice) -> None:
    """Recompute invoice status from its net paid amount."""
    if invoice.is_auto and invoice.status == InvoiceStatus.DRAFT:
        # Auto (statement) invoices stay DRAFT while open: DRAFT means "live
        # internal statement". Paid/balance is derived from allocations minus
        # credits, never from the status, so skip the mutation entirely.
        return
    net_paid = await _invoice_net_paid(session, invoice_id=invoice.id)

    if net_paid >= Decimal(invoice.total):
        invoice.status = InvoiceStatus.PAID
    elif net_paid > Decimal("0"):
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = InvoiceStatus.ISSUED
    await session.flush()


# ── CRUD ────────────────────────────────────────────────────────────────────


async def record_transaction(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    method: PaymentMethod,
    reference_note: str | None,
    recorded_at: datetime | None,
    allocations: list[Any] | None,
    actor_id: uuid.UUID,
    direction: TransactionDirection = TransactionDirection.DEBIT,
) -> Transaction:
    """Record a payment (DEBIT) against an issued, partially paid, or
    auto (statement) DRAFT invoice.

    Auto statement invoices in DRAFT accept payments as live internal
    statements (the status never leaves DRAFT). The portion of the payment
    that exceeds the invoice's remaining balance is turned into an Advance
    (client-scoped, or unassigned for general invoices). Returns the created
    Transaction with allocations eager-loaded.
    """
    invoice = await _get_invoice_with_items(session, tenant_id, invoice_id)
    if invoice is None:
        raise TransactionInvoiceNotFoundError()

    payable = invoice.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID) or (
        invoice.is_auto and invoice.status == InvoiceStatus.DRAFT
    )
    if not payable:
        if invoice.status == InvoiceStatus.PAID:
            raise TransactionAlreadyPaidError()
        raise TransactionNotPayableError()

    if amount <= 0:
        raise TransactionInvalidAmountError()

    net_paid = await _invoice_net_paid(session, invoice_id=invoice.id)
    remaining = _money(Decimal(invoice.total) - net_paid)
    excess = Decimal("0")
    applied = _money(amount)
    if amount > remaining:
        applied = remaining
        excess = _money(amount - remaining)

    if direction == TransactionDirection.DEBIT:
        if allocations is not None:
            alloc_data = await _validate_allocations(invoice, amount, allocations)
        else:
            alloc_data = await _auto_allocate(invoice, applied)
    else:
        # Credit transactions (refunds) carry no allocations.
        alloc_data = []

    tx = Transaction(
        invoice_id=invoice.id,
        amount=_money(amount),
        direction=direction,
        method=method,
        reference_note=reference_note or "",
        recorded_by_id=actor_id,
    )
    if recorded_at is not None:
        tx.recorded_at = recorded_at
    session.add(tx)
    await session.flush()
    for data in alloc_data:
        session.add(PaymentAllocation(transaction_id=tx.id, **data))

    advance_id: uuid.UUID | None = None
    if direction == TransactionDirection.DEBIT and excess > Decimal("0"):
        client_id = invoice.project.client_id if invoice.project else None
        advance = Advance(
            tenant_id=invoice.tenant_id,
            client_id=client_id,
            amount=excess,
            remaining_amount=excess,
            source_invoice_id=invoice.id,
            created_by_id=actor_id,
            created_by_type=ActorType.ADMIN_USER.value,
        )
        session.add(advance)
        await session.flush()
        advance_id = advance.id
        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="invoice.advance_received",
            entity_type="advance",
            entity_id=str(advance.id),
            details={
                "invoice_id": str(invoice.id),
                "amount": f"{excess:.2f}",
                "client_id": str(client_id) if client_id else None,
            },
        )

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.payment_recorded",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={
            "invoice_id": str(invoice.id),
            "amount": f"{_money(amount):.2f}",
            "method": method.value,
            "direction": direction.value,
            "advance_id": str(advance_id) if advance_id else None,
        },
    )

    await _recompute_invoice_status(session, invoice)
    await session.commit()

    if tx.direction == TransactionDirection.DEBIT:
        await safe_notify(notify_payment_recorded(session, transaction_id=tx.id))

    # Re-fetch with allocations eager-loaded (fresh after commit).
    fresh_q = (
        select(Transaction)
        .options(selectinload(Transaction.allocations))
        .where(Transaction.id == tx.id)
    )
    fresh = (await session.execute(fresh_q)).unique().scalar_one_or_none()
    return fresh if fresh is not None else tx


async def refund_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    method: PaymentMethod,
    reference_note: str | None,
    actor_id: uuid.UUID,
) -> Transaction:
    """Record a refund (CREDIT transaction, no allocations) against an invoice.

    Allowed on issued/partially paid/paid invoices and on auto (statement)
    invoices in DRAFT; other states are not payable. The refund cannot exceed
    the invoice's net paid amount. Returns the created Transaction with
    allocations eager-loaded.
    """
    invoice = await _get_invoice_with_items(session, tenant_id, invoice_id)
    if invoice is None:
        raise TransactionInvoiceNotFoundError()

    payable = invoice.status in (
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.PAID,
    ) or (invoice.is_auto and invoice.status == InvoiceStatus.DRAFT)
    if not payable:
        raise TransactionNotPayableError()

    if amount <= 0:
        raise TransactionInvalidAmountError()

    net_paid = await _invoice_net_paid(session, invoice_id=invoice.id)
    if _money(amount) > net_paid:
        raise RefundExceedsPaidError()

    tx = Transaction(
        invoice_id=invoice.id,
        amount=_money(amount),
        direction=TransactionDirection.CREDIT,
        method=method or PaymentMethod.OTHER,
        reference_note=reference_note or "",
        recorded_by_id=actor_id,
    )
    session.add(tx)
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.refunded",
        entity_type="transaction",
        entity_id=str(tx.id),
        details={
            "invoice_id": str(invoice.id),
            "amount": f"{_money(amount):.2f}",
            "method": (method or PaymentMethod.OTHER).value,
        },
    )

    await _recompute_invoice_status(session, invoice)
    await session.commit()

    await safe_notify(notify_refund_recorded(session, transaction_id=tx.id))

    fresh_q = (
        select(Transaction)
        .options(selectinload(Transaction.allocations))
        .where(Transaction.id == tx.id)
    )
    fresh = (await session.execute(fresh_q)).unique().scalar_one_or_none()
    return fresh if fresh is not None else tx


async def apply_advance(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal | None,
    actor_id: uuid.UUID,
) -> dict[str, str]:
    """Apply client advance balance to an issued/partially paid invoice, or
    to an auto (statement) invoice in DRAFT.

    Advance scope matches the invoice: client-scoped when the invoice has a
    project, unassigned (client_id NULL) for general invoices. Advances are
    consumed oldest-first. Returns {"applied", "advance_balance"} as f2.
    """
    invoice = await _get_invoice_with_items(session, tenant_id, invoice_id)
    if invoice is None:
        raise TransactionInvoiceNotFoundError()

    payable = invoice.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID) or (
        invoice.is_auto and invoice.status == InvoiceStatus.DRAFT
    )
    if not payable:
        raise ApplyAdvanceError()

    client_id = invoice.project.client_id if invoice.project else None
    adv_stmt = (
        select(Advance)
        .where(
            Advance.tenant_id == tenant_id,
            Advance.client_id == client_id,
            Advance.remaining_amount > 0,
        )
        .order_by(Advance.created_at.asc())
    )
    advances = list((await session.execute(adv_stmt)).scalars().all())
    available = _money(sum((adv.remaining_amount for adv in advances), Decimal("0")))

    needed = _money(
        Decimal(invoice.total) - await _invoice_net_paid(session, invoice_id=invoice.id)
    )
    if needed <= 0:
        raise AdvanceUnavailableError("Invoice already fully paid")

    if amount is not None:
        if amount <= 0:
            raise ApplyAdvanceError("Advance application amount must be positive")
        if _money(amount) > available:
            raise AdvanceUnavailableError("Advance balance insufficient")
        if _money(amount) > needed:
            raise ApplyAdvanceError("Applied amount exceeds invoice balance")
        apply = _money(amount)
    else:
        apply = min(available, needed)

    if apply <= 0:
        raise AdvanceUnavailableError()

    apply_left = apply
    for advance in advances:
        if apply_left <= 0:
            break
        take = min(advance.remaining_amount, apply_left)
        advance.remaining_amount = _money(advance.remaining_amount - take)
        apply_left = _money(apply_left - take)
        for data in await _auto_allocate(invoice, take):
            session.add(
                PaymentAllocation(
                    transaction_id=None,
                    advance_id=advance.id,
                    **data,
                )
            )
    await session.flush()

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.advance_applied",
        entity_type="advance",
        details={
            "invoice_id": str(invoice.id),
            "amount": f"{apply:.2f}",
        },
    )

    await _recompute_invoice_status(session, invoice)
    await session.commit()

    await safe_notify(notify_advance_applied(session, invoice_id=invoice.id, amount=apply))

    return {
        "applied": f"{apply:.2f}",
        "advance_balance": f"{_money(available - apply):.2f}",
    }


async def list_transactions(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> list[Transaction]:
    """List payments/refunds recorded against an invoice (oldest first)."""
    invoice = await _get_invoice_with_items(session, tenant_id, invoice_id)
    if invoice is None:
        raise TransactionInvoiceNotFoundError()

    stmt = (
        select(Transaction)
        .options(selectinload(Transaction.allocations))
        .where(Transaction.invoice_id == invoice_id)
        .order_by(Transaction.recorded_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.unique().scalars().all())


# ── Ledger (FEAT-015, TODO-158) ─────────────────────────────────────────────


async def build_client_ledger(
    session: AsyncSession, *, tenant_id: uuid.UUID, client_id: uuid.UUID
) -> dict[str, Any]:
    """Client ledger: advance balance + chronological signed money entries.

    Entries combine the client's invoice transactions (payments + refunds,
    client-linked invoices only), the client's advance receipts, and advance
    applications (allocations on the client's invoices). Running balance is
    the cumulative sum of the signed entry amounts.
    """
    entries: list[dict[str, Any]] = []

    tx_rows = (
        (
            await session.execute(
                select(Transaction)
                .join(Invoice, Transaction.invoice_id == Invoice.id)
                .join(Project, Invoice.project_id == Project.id)
                .where(
                    Invoice.tenant_id == tenant_id,
                    Project.client_id == client_id,
                )
                .order_by(Transaction.recorded_at.asc())
            )
        )
        .unique()
        .scalars()
        .all()
    )
    for tx in tx_rows:
        if tx.direction == TransactionDirection.CREDIT:
            entries.append(
                {
                    "id": tx.id,
                    "kind": "refund",
                    "amount": f"-{_money(tx.amount):.2f}",
                    "reference": tx.reference_note,
                    "invoice_id": tx.invoice_id,
                    "created_at": tx.recorded_at,
                    "_value": -_money(tx.amount),
                    "_ts": tx.recorded_at,
                    "_prio": 2,
                }
            )
        else:
            entries.append(
                {
                    "id": tx.id,
                    "kind": "payment",
                    "amount": f"{_money(tx.amount):.2f}",
                    "reference": tx.reference_note,
                    "invoice_id": tx.invoice_id,
                    "created_at": tx.recorded_at,
                    "_value": _money(tx.amount),
                    "_ts": tx.recorded_at,
                    "_prio": 0,
                }
            )

    adv_rows = (
        (
            await session.execute(
                select(Advance).where(
                    Advance.tenant_id == tenant_id,
                    Advance.client_id == client_id,
                )
            )
        )
        .scalars()
        .all()
    )
    for advance in adv_rows:
        entries.append(
            {
                "id": advance.id,
                "kind": "advance_received",
                "amount": f"-{_money(advance.amount):.2f}",
                "reference": "",
                "invoice_id": advance.source_invoice_id,
                "created_at": advance.created_at,
                "_value": -_money(advance.amount),
                "_ts": advance.created_at,
                "_prio": 1,
            }
        )

    applied_rows = (
        await session.execute(
            select(
                PaymentAllocation.id,
                InvoiceLineItem.invoice_id,
                PaymentAllocation.amount,
                PaymentAllocation.created_at,
            )
            .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
            .join(Advance, PaymentAllocation.advance_id == Advance.id)
            .where(
                PaymentAllocation.transaction_id.is_(None),
                PaymentAllocation.advance_id.is_not(None),
                Advance.tenant_id == tenant_id,
                Advance.client_id == client_id,
            )
            .order_by(PaymentAllocation.created_at.asc())
        )
    ).all()
    for alloc_id, invoice_id, alloc_amount, created_at in applied_rows:
        entries.append(
            {
                "id": alloc_id,
                "kind": "advance_applied",
                "amount": f"{_money(alloc_amount):.2f}",
                "reference": "",
                "invoice_id": invoice_id,
                "created_at": created_at,
                "_value": _money(alloc_amount),
                "_ts": created_at,
                "_prio": 3,
            }
        )

    entries.sort(key=lambda e: (e["_ts"], e["_prio"]))

    running = Decimal("0")
    for entry in entries:
        running = _money(running + entry["_value"])
        entry["running_balance"] = f"{running:.2f}"

    advance_balance = _money(sum((adv.remaining_amount for adv in adv_rows), Decimal("0")))

    return {
        "advance_balance": f"{advance_balance:.2f}",
        "entries": [
            {key: value for key, value in entry.items() if not key.startswith("_")}
            for entry in entries
        ],
    }
