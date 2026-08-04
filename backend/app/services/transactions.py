"""Invoice transaction business logic (FEAT-009, TODO-089/090/092/093/094).

Owns the orchestration of:
- Recording a payment against an issued/partially-paid invoice
- Auto proportional allocation of a payment across line items (TODO-094)
- Manual allocation override validation
- Invoice status recompute after payment (PARTIALLY_PAID / PAID)
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

from app.models.enums import ActorType, InvoiceStatus, PaymentMethod
from app.models.invoice import Invoice
from app.models.transaction import PaymentAllocation, Transaction
from app.services.audit import log as audit_log

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


# ── Helpers ─────────────────────────────────────────────────────────────────


def _money(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_invoice_with_items(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Fetch an invoice with line_items eager-loaded, tenant-scoped."""
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .execution_options(populate_existing=True)
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


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
    """Recompute invoice status from the sum of its transaction amounts."""
    paid_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.invoice_id == invoice.id
    )
    paid_sum = Decimal((await session.execute(paid_q)).scalar_one())

    if paid_sum >= Decimal(invoice.total):
        invoice.status = InvoiceStatus.PAID
    elif paid_sum > Decimal("0"):
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
) -> Transaction:
    """Record a payment against an issued or partially paid invoice.

    Returns the created Transaction with allocations eager-loaded.
    """
    invoice = await _get_invoice_with_items(session, tenant_id, invoice_id)
    if invoice is None:
        raise TransactionInvoiceNotFoundError()

    if invoice.status not in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID):
        if invoice.status == InvoiceStatus.PAID:
            raise TransactionAlreadyPaidError()
        raise TransactionNotPayableError()

    if amount <= 0:
        raise TransactionInvalidAmountError()

    if allocations is not None:
        alloc_data = await _validate_allocations(invoice, amount, allocations)
    else:
        alloc_data = await _auto_allocate(invoice, amount)

    tx = Transaction(
        invoice_id=invoice.id,
        amount=_money(amount),
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
        },
    )

    await _recompute_invoice_status(session, invoice)
    await session.commit()

    # Re-fetch with allocations eager-loaded (fresh after commit).
    fresh_q = (
        select(Transaction)
        .options(selectinload(Transaction.allocations))
        .where(Transaction.id == tx.id)
    )
    fresh = (await session.execute(fresh_q)).unique().scalar_one_or_none()
    return fresh if fresh is not None else tx


async def list_transactions(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> list[Transaction]:
    """List payments recorded against an invoice (oldest first)."""
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
