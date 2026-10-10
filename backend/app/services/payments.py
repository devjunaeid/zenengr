"""Unified Payment service (FEAT-027, TODO-222).

Single source of truth for client payments and refunds.
- Records payments with FIFO auto-allocation across open invoices or explicit target invoices.
- Unallocated amount = Client Advance credit.
- Supports soft-delete (void) with optional reason and 1-click restore per ADR-004.
- Audits all actions with structured details.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_user import AdminUser
from app.models.client import Client
from app.models.enums import (
    ActorType,
    InvoiceStatus,
    LedgerEntryType,
    LedgerSourceType,
    PaymentKind,
    PaymentMethod,
    TransactionDirection,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.ledger_entry import LedgerEntry
from app.models.payment import Payment
from app.models.project import Project
from app.models.transaction import PaymentAllocation, Transaction
from app.schemas.payments import PaymentAllocationItem, PaymentResponse
from app.services.audit import log as audit_log


def _money(value: Decimal | int | float | str) -> Decimal:
    """Round to 2 decimal places, half-up."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_payment_with_allocations(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
) -> Payment:
    stmt = (
        select(Payment)
        .where(Payment.id == payment_id, Payment.tenant_id == tenant_id)
        .options(
            selectinload(Payment.allocations).selectinload(PaymentAllocation.transaction),
        )
    )
    payment = (await session.execute(stmt)).scalar_one_or_none()
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


async def payment_to_response(session: AsyncSession, payment: Payment) -> PaymentResponse:
    # calculate active allocations
    active_allocs = [a for a in payment.allocations if a.voided_at is None]
    allocated = sum((_money(a.amount) for a in active_allocs), Decimal("0"))
    unallocated = max(_money(payment.amount) - allocated, Decimal("0"))

    # batch-resolve invoice numbers for line items
    items: list[PaymentAllocationItem] = []
    if payment.allocations:
        li_ids = [a.line_item_id for a in payment.allocations]
        li_stmt = (
            select(InvoiceLineItem.id, Invoice.id, Invoice.invoice_number)
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .where(InvoiceLineItem.id.in_(li_ids))
        )
        li_rows = (await session.execute(li_stmt)).all()
        inv_map = {row[0]: (row[1], row[2]) for row in li_rows}

        for a in payment.allocations:
            inv_info = inv_map.get(a.line_item_id, (None, None))
            items.append(
                PaymentAllocationItem(
                    id=a.id,
                    line_item_id=a.line_item_id,
                    amount=f"{a.amount:.2f}",
                    invoice_id=inv_info[0],
                    invoice_number=inv_info[1],
                    voided_at=a.voided_at,
                )
            )

    return PaymentResponse(
        id=payment.id,
        tenant_id=payment.tenant_id,
        client_id=payment.client_id,
        project_id=payment.project_id,
        kind=payment.kind,
        amount=f"{payment.amount:.2f}",
        method=payment.method,
        paid_on=payment.paid_on,
        reference_note=payment.reference_note,
        notes=payment.notes,
        allocated_amount=f"{allocated:.2f}",
        unallocated_amount=f"{unallocated:.2f}",
        allocations=items,
        voided_at=payment.voided_at,
        void_reason=payment.void_reason,
        created_at=payment.created_at,
    )


async def _recompute_invoice_balance_and_status(session: AsyncSession, invoice_id: uuid.UUID) -> None:
    """Recomputes status for an invoice considering only active allocations and transactions."""
    invoice = await session.get(Invoice, invoice_id)
    if not invoice or (invoice.is_auto and invoice.status == InvoiceStatus.DRAFT):
        return

    debit_tx_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.invoice_id == invoice_id,
        Transaction.direction == TransactionDirection.DEBIT,
        Transaction.voided_at.is_(None),
    )
    debit_tx = Decimal((await session.execute(debit_tx_q)).scalar_one())

    adv_q = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .where(
            InvoiceLineItem.invoice_id == invoice_id,
            PaymentAllocation.transaction_id.is_(None),
            PaymentAllocation.advance_id.is_not(None),
            PaymentAllocation.voided_at.is_(None),
        )
    )
    adv_applied = Decimal((await session.execute(adv_q)).scalar_one())

    credit_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.invoice_id == invoice_id,
        Transaction.direction == TransactionDirection.CREDIT,
        Transaction.voided_at.is_(None),
    )
    credits = Decimal((await session.execute(credit_q)).scalar_one())

    net_paid = _money(debit_tx + adv_applied - credits)

    if Decimal(invoice.total) > Decimal("0") and net_paid >= Decimal(invoice.total):
        invoice.status = InvoiceStatus.PAID
    elif net_paid > Decimal("0"):
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    else:
        invoice.status = InvoiceStatus.ISSUED
    await session.flush()


async def _allocate_to_invoice(
    session: AsyncSession,
    *,
    payment: Payment,
    invoice: Invoice,
    amount_to_allocate: Decimal,
    actor_id: uuid.UUID | None,
) -> Decimal:
    """Allocates a portion of payment to a specific invoice proportionally across line items."""
    amount_to_allocate = _money(amount_to_allocate)
    if amount_to_allocate <= Decimal("0"):
        return Decimal("0")

    # calculate invoice balance due
    debit_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.invoice_id == invoice.id,
        Transaction.direction == TransactionDirection.DEBIT,
        Transaction.voided_at.is_(None),
    )
    debits = Decimal((await session.execute(debit_q)).scalar_one())
    due = max(_money(invoice.total) - debits, Decimal("0"))
    alloc_amount = min(amount_to_allocate, due)
    if alloc_amount <= Decimal("0"):
        return Decimal("0")

    # proportional line item split (largest remainder method)
    line_items = sorted(invoice.line_items, key=lambda li: li.created_at)
    if not line_items:
        return Decimal("0")

    total_cents = int(_money(invoice.total) * 100)
    alloc_cents = int(alloc_amount * 100)

    # create a Transaction record linked to this payment
    tx = Transaction(
        invoice_id=invoice.id,
        payment_id=payment.id,
        amount=alloc_amount,
        direction=TransactionDirection.DEBIT if payment.kind == PaymentKind.RECEIPT else TransactionDirection.CREDIT,
        method=payment.method,
        reference_note=payment.reference_note or f"Payment {payment.id.hex[:8]}",
        recorded_by_id=actor_id,
        recorded_at=datetime.combine(payment.paid_on, datetime.min.time(), tzinfo=UTC),
    )
    session.add(tx)
    await session.flush()

    if total_cents <= 0:
        session.add(
            PaymentAllocation(
                payment_id=payment.id,
                transaction_id=tx.id,
                line_item_id=line_items[0].id,
                amount=alloc_amount,
            )
        )
    else:
        shares = []
        for li in line_items:
            li_cents = int(_money(li.amount) * 100)
            shares.append(
                {
                    "line_item_id": li.id,
                    "amount": (alloc_cents * li_cents) // total_cents,
                    "frac": (alloc_cents * li_cents) % total_cents,
                }
            )
        remainder = alloc_cents - sum(s["amount"] for s in shares)
        for s in sorted(shares, key=lambda s: s["frac"], reverse=True):
            if remainder <= 0:
                break
            s["amount"] += 1
            remainder -= 1

        for s in shares:
            item_amt = _money(Decimal(s["amount"]) / Decimal("100"))
            if item_amt > 0:
                session.add(
                    PaymentAllocation(
                        payment_id=payment.id,
                        transaction_id=tx.id,
                        line_item_id=s["line_item_id"],
                        amount=item_amt,
                    )
                )

    await session.flush()
    await _recompute_invoice_balance_and_status(session, invoice.id)
    return alloc_amount


async def record_payment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    amount: Decimal,
    kind: PaymentKind = PaymentKind.RECEIPT,
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER,
    paid_on: date | None = None,
    reference_note: str = "",
    notes: str = "",
    actor_id: uuid.UUID | None = None,
    auto_allocate: bool = True,
    invoice_id: uuid.UUID | None = None,
    allocations: list[Any] | None = None,
) -> Payment:
    """Record a payment (Money In) or refund.

    Single source of truth per FEAT-027.
    """
    amount = _money(amount)
    if amount <= Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Payment amount must be greater than 0",
        )

    project: Project | None = None
    if project_id is not None:
        project = await session.get(Project, project_id)
        if project is None or project.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        if client_id is None:
            client_id = project.client_id

    if client_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Client ID is required",
        )

    client = await session.get(Client, client_id)
    if client is None or client.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    payment = Payment(
        tenant_id=tenant_id,
        client_id=client_id,
        project_id=project_id,
        kind=kind,
        amount=amount,
        method=method,
        paid_on=paid_on or date.today(),
        reference_note=reference_note.strip(),
        notes=notes.strip(),
        recorded_by_id=actor_id,
    )
    session.add(payment)
    await session.flush()

    remaining = amount

    # 1. Explicit invoice allocations if specified
    if allocations:
        alloc_total = sum((_money(a.amount if hasattr(a, "amount") else a["amount"]) for a in allocations), Decimal("0"))
        if alloc_total > amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total allocation ({alloc_total}) exceeds payment amount ({amount})",
            )
        for item in allocations:
            inv_id = item.invoice_id if hasattr(item, "invoice_id") else item["invoice_id"]
            alloc_amt = _money(item.amount if hasattr(item, "amount") else item["amount"])
            inv_stmt = (
                select(Invoice)
                .where(Invoice.id == inv_id, Invoice.tenant_id == tenant_id)
                .options(selectinload(Invoice.line_items))
            )
            target_inv = (await session.execute(inv_stmt)).scalar_one_or_none()
            if target_inv and target_inv.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID):
                allocated = await _allocate_to_invoice(
                    session,
                    payment=payment,
                    invoice=target_inv,
                    amount_to_allocate=alloc_amt,
                    actor_id=actor_id,
                )
                remaining -= allocated

    # 2. Target single invoice allocation if specified
    elif invoice_id is not None:
        inv_stmt = (
            select(Invoice)
            .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
            .options(selectinload(Invoice.line_items))
        )
        target_inv = (await session.execute(inv_stmt)).scalar_one_or_none()
        if target_inv and target_inv.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID):
            allocated = await _allocate_to_invoice(
                session,
                payment=payment,
                invoice=target_inv,
                amount_to_allocate=remaining,
                actor_id=actor_id,
            )
            remaining -= allocated

    # 3. FIFO Auto-allocation to open invoices if enabled
    elif auto_allocate and kind == PaymentKind.RECEIPT:
        inv_q = (
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_((InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID)),
            )
            .options(selectinload(Invoice.line_items))
        )
        if project_id is not None:
            inv_q = inv_q.where(Invoice.project_id == project_id)
        else:
            inv_q = inv_q.join(Project, Invoice.project_id == Project.id).where(
                Project.client_id == client_id
            )

        inv_q = inv_q.order_by(Invoice.due_date.asc().nulls_last(), Invoice.created_at.asc())
        open_invoices = list((await session.execute(inv_q)).scalars().all())

        for inv in open_invoices:
            if remaining <= Decimal("0"):
                break
            allocated = await _allocate_to_invoice(
                session,
                payment=payment,
                invoice=inv,
                amount_to_allocate=remaining,
                actor_id=actor_id,
            )
            remaining -= allocated

    # 3. Create backing LedgerEntry for project ledger timeline
    if project_id is not None:
        formatted_method = method.value.replace("_", " ").title()
        desc = (
            f"{formatted_method} - {reference_note}".strip(" -")
            if reference_note
            else formatted_method
        )
        ledger_entry = LedgerEntry(
            project_id=project_id,
            type=LedgerEntryType.PAYMENT if kind == PaymentKind.RECEIPT else LedgerEntryType.REFUND,
            amount=amount,
            description=desc,
            source_type=LedgerSourceType.TRANSACTION,
            source_id=payment.id,
            entry_date=payment.paid_on,
            created_by_id=actor_id,
        )
        session.add(ledger_entry)

    # 4. Audit Log
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id or uuid.UUID(int=0),
        actor_type=ActorType.ADMIN_USER,
        action="payment.recorded",
        entity_type="payment",
        entity_id=str(payment.id),
        details={
            "amount": f"{amount:.2f}",
            "kind": kind.value,
            "method": method.value,
            "project_id": str(project_id) if project_id else None,
            "client_id": str(client_id),
            "allocated": f"{amount - remaining:.2f}",
            "unallocated_advance": f"{remaining:.2f}",
        },
    )

    await session.commit()
    return await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment.id)


async def void_payment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    reason: str = "",
    actor_id: uuid.UUID | None = None,
) -> Payment:
    """Soft-deletes (voids) a payment, its allocations and transactions per ADR-004."""
    payment = await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment_id)
    if payment.voided_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment is already voided",
        )

    now = datetime.now(UTC)
    payment.voided_at = now
    payment.voided_by_id = actor_id
    payment.void_reason = reason.strip()

    affected_invoice_ids: set[uuid.UUID] = set()

    for alloc in payment.allocations:
        alloc.voided_at = now
        if alloc.transaction:
            alloc.transaction.voided_at = now
            affected_invoice_ids.add(alloc.transaction.invoice_id)

    # void matching ledger entry if any
    ledger_stmt = select(LedgerEntry).where(
        LedgerEntry.source_id == payment.id,
        LedgerEntry.voided_at.is_(None),
    )
    ledger_entries = list((await session.execute(ledger_stmt)).scalars().all())
    for le in ledger_entries:
        le.voided_at = now
        le.voided_by_id = actor_id
        le.void_reason = reason.strip()

    await session.flush()

    for inv_id in affected_invoice_ids:
        await _recompute_invoice_balance_and_status(session, inv_id)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id or uuid.UUID(int=0),
        actor_type=ActorType.ADMIN_USER,
        action="payment.voided",
        entity_type="payment",
        entity_id=str(payment.id),
        details={"reason": reason, "amount": f"{payment.amount:.2f}"},
    )

    await session.commit()
    return await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment.id)


async def restore_payment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
) -> Payment:
    """Restores a voided payment in 1 click per ADR-004."""
    payment = await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment_id)
    if payment.voided_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment is not voided",
        )

    payment.voided_at = None
    payment.voided_by_id = None
    payment.void_reason = ""

    affected_invoice_ids: set[uuid.UUID] = set()

    for alloc in payment.allocations:
        alloc.voided_at = None
        if alloc.transaction:
            alloc.transaction.voided_at = None
            affected_invoice_ids.add(alloc.transaction.invoice_id)

    ledger_stmt = select(LedgerEntry).where(
        LedgerEntry.source_id == payment.id,
        LedgerEntry.voided_at.is_not(None),
    )
    ledger_entries = list((await session.execute(ledger_stmt)).scalars().all())
    for le in ledger_entries:
        le.voided_at = None
        le.voided_by_id = None
        le.void_reason = ""

    await session.flush()

    for inv_id in affected_invoice_ids:
        await _recompute_invoice_balance_and_status(session, inv_id)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id or uuid.UUID(int=0),
        actor_type=ActorType.ADMIN_USER,
        action="payment.restored",
        entity_type="payment",
        entity_id=str(payment.id),
        details={"amount": f"{payment.amount:.2f}"},
    )

    await session.commit()
    return await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment.id)


async def update_payment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    amount: Decimal | None = None,
    method: PaymentMethod | None = None,
    paid_on: date | None = None,
    reference_note: str | None = None,
    notes: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> Payment:
    """Update payment fields. Flexible per ADR-004."""
    payment = await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment_id)
    if payment.voided_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update a voided payment. Restore it first.",
        )

    before_state = {
        "amount": f"{payment.amount:.2f}",
        "method": payment.method.value,
        "paid_on": str(payment.paid_on),
        "reference_note": payment.reference_note,
    }

    if amount is not None:
        new_amt = _money(amount)
        allocated = sum((_money(a.amount) for a in payment.allocations if a.voided_at is None), Decimal("0"))
        if new_amt < allocated:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Amount cannot be less than allocated amount ({allocated:.2f}). Void or re-allocate first.",
            )
        payment.amount = new_amt

    if method is not None:
        payment.method = method
    if paid_on is not None:
        payment.paid_on = paid_on
    if reference_note is not None:
        payment.reference_note = reference_note.strip()
    if notes is not None:
        payment.notes = notes.strip()

    # update matching ledger entry description/amount if any
    ledger_stmt = select(LedgerEntry).where(
        LedgerEntry.source_id == payment.id,
        LedgerEntry.voided_at.is_(None),
    )
    for le in (await session.execute(ledger_stmt)).scalars().all():
        le.amount = payment.amount
        le.entry_date = payment.paid_on
        formatted_method = payment.method.value.replace("_", " ").title()
        le.description = (
            f"{formatted_method} - {payment.reference_note}".strip(" -")
            if payment.reference_note
            else formatted_method
        )

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id or uuid.UUID(int=0),
        actor_type=ActorType.ADMIN_USER,
        action="payment.updated",
        entity_type="payment",
        entity_id=str(payment.id),
        details={
            "before": before_state,
            "after": {
                "amount": f"{payment.amount:.2f}",
                "method": payment.method.value,
                "paid_on": str(payment.paid_on),
                "reference_note": payment.reference_note,
            },
        },
    )

    await session.commit()
    return await _get_payment_with_allocations(session, tenant_id=tenant_id, payment_id=payment.id)


async def list_project_payments(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    include_voided: bool = True,
) -> list[Payment]:
    """List payments for a project."""
    stmt = (
        select(Payment)
        .where(Payment.tenant_id == tenant_id, Payment.project_id == project_id)
        .options(
            selectinload(Payment.allocations).selectinload(PaymentAllocation.transaction),
        )
        .order_by(Payment.paid_on.desc(), Payment.created_at.desc())
    )
    if not include_voided:
        stmt = stmt.where(Payment.voided_at.is_(None))
    return list((await session.execute(stmt)).scalars().all())
