"""Project ledger (FEAT-018): append-only charges + derived payment stream.

The ledger persists charges and manual adjustments only (LedgerEntry rows,
type CHARGE, signed amounts). The payment stream is derived at read time
from the existing Transaction stream on the project's non-draft invoices -
no mirror writes. FR-18.2, FR-18.4.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ActorType,
    DiscountType,
    InvoiceStatus,
    LedgerEntryType,
    LedgerSourceType,
    TransactionDirection,
)
from app.models.invoice import Invoice
from app.models.ledger_entry import LedgerEntry
from app.models.project import Project
from app.models.transaction import Transaction
from app.services.audit import log as audit_log


class DiscountValidationError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )


def _money(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_project(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project:
    """Fetch a project scoped to a tenant. 404 (ProjectNotFoundError) otherwise."""
    # Lazy import to avoid a module-level cycle with app.services.projects
    # (projects.py imports this module for its charge hooks).
    from app.services.projects import ProjectNotFoundError

    stmt = select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    project = (await session.execute(stmt)).scalar_one_or_none()
    if project is None:
        raise ProjectNotFoundError()
    return project


# ── Charge hooks (FR-18.5) ──────────────────────────────────────────────────


async def add_service_charge(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
    amount: Decimal,
    description: str,
    actor_id: uuid.UUID | None = None,
) -> LedgerEntry:
    """Record a positive charge for an attached project service.

    Signed amount (normal charge positive). No commit; the caller commits.
    """
    entry = LedgerEntry(
        project_id=project_id,
        type=LedgerEntryType.CHARGE,
        amount=_money(amount),
        description=description,
        source_type=LedgerSourceType.PROJECT_SERVICE,
        source_id=project_service_id,
        entry_date=date.today(),
        created_by_id=actor_id,
    )
    session.add(entry)
    return entry


async def add_service_reversal(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
    amount: Decimal,
    description: str,
    actor_id: uuid.UUID | None = None,
) -> LedgerEntry:
    """Record an OFFSETTING negative charge when a service is removed/cancelled.

    Keeps the ledger honest: the original attach charge stays on the
    timeline, and this reversal brings the subtotal back down. No commit;
    the caller commits.
    """
    entry = LedgerEntry(
        project_id=project_id,
        type=LedgerEntryType.CHARGE,
        amount=_money(-amount),
        description=description,
        source_type=LedgerSourceType.PROJECT_SERVICE,
        source_id=project_service_id,
        entry_date=date.today(),
        created_by_id=actor_id,
    )
    session.add(entry)
    return entry


async def add_manual_adjustment(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    amount: Decimal,
    description: str,
    actor_id: uuid.UUID,
) -> LedgerEntry:
    """Record a signed manual adjustment (positive adds, negative reduces).

    Audited (project.ledger_adjusted) and committed. 404 if the project does
    not exist in the tenant.
    """
    project = await _get_project(session, tenant_id, project_id)

    entry = LedgerEntry(
        project_id=project.id,
        type=LedgerEntryType.CHARGE,
        amount=_money(amount),
        description=description,
        source_type=LedgerSourceType.MANUAL_ADJUSTMENT,
        entry_date=date.today(),
        created_by_id=actor_id,
    )
    session.add(entry)

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="project.ledger_adjusted",
        entity_type="project",
        entity_id=str(project.id),
        details={"amount": f"{_money(amount):.2f}", "description": description},
    )
    await session.commit()
    await session.refresh(entry)
    return entry


# ── Ledger read (TODO-180) ─────────────────────────────────────────────────


async def get_project_ledger(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> dict[str, Any]:
    """Build the project ledger: merged chronological entries + live summary.

    Entries combine persisted charges (LedgerEntry rows) with the derived
    payment stream (Transactions on the project's non-draft invoices).
    Summary math per FR-18.4. 404 if the project is not in the tenant.
    """
    project = await _get_project(session, tenant_id, project_id)

    # ── Persisted charges (append-only) ─────────────────────────────────────
    charge_q = (
        select(LedgerEntry)
        .where(LedgerEntry.project_id == project.id)
        .order_by(LedgerEntry.entry_date, LedgerEntry.created_at)
    )
    charges = list((await session.execute(charge_q)).scalars().all())

    # ── Derived payment stream (FR-18.2; no mirror writes) ──────────────────
    tx_q = (
        select(Transaction, Invoice)
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.project_id == project.id,
            Invoice.status != InvoiceStatus.DRAFT,
        )
        .order_by(Transaction.recorded_at, Transaction.created_at)
    )
    tx_rows = (await session.execute(tx_q)).all()

    entries: list[dict[str, Any]] = []
    for ch in charges:
        entries.append(
            {
                "id": ch.id,
                "type": ch.type,
                "amount": f"{ch.amount:.2f}",
                "description": ch.description,
                "source_type": ch.source_type,
                "source_id": ch.source_id,
                "invoice_ref": ch.invoice_ref,
                "invoice_number": None,
                "entry_date": ch.entry_date,
                "created_at": ch.created_at,
            }
        )

    for tx, invoice in tx_rows:
        if tx.direction == TransactionDirection.DEBIT:
            entry_type = LedgerEntryType.PAYMENT
            amount_str = f"{_money(tx.amount):.2f}"
        else:
            entry_type = LedgerEntryType.REFUND
            amount_str = f"-{_money(tx.amount):.2f}"
        entries.append(
            {
                "id": tx.id,
                "type": entry_type,
                "amount": amount_str,
                "description": f"{tx.method.value} {tx.reference_note}".strip(),
                "source_type": LedgerSourceType.TRANSACTION,
                "source_id": tx.id,
                "invoice_ref": invoice.id,
                "invoice_number": None,
                "entry_date": tx.recorded_at.date(),
                "created_at": tx.recorded_at,
            }
        )

    # Batch-resolve invoice numbers for every entry carrying an invoice_ref.
    invoice_ids = sorted({e["invoice_ref"] for e in entries if e["invoice_ref"] is not None})
    number_map: dict[uuid.UUID, str | None] = {}
    if invoice_ids:
        num_rows = (
            await session.execute(
                select(Invoice.id, Invoice.invoice_number).where(Invoice.id.in_(invoice_ids))
            )
        ).all()
        for inv_id, inv_number in num_rows:
            number_map[inv_id] = inv_number
    for e in entries:
        if e["invoice_ref"] is not None:
            e["invoice_number"] = number_map.get(e["invoice_ref"])

    # ── Live summary (FR-18.4) ──────────────────────────────────────────────
    subtotal = _money(
        sum((ch.amount for ch in charges if ch.type == LedgerEntryType.CHARGE), Decimal("0"))
    )
    discount_type = project.discount_type
    discount_value = project.discount_value
    discount_amount = Decimal("0")
    if subtotal > 0 and discount_type is not None and discount_value is not None:
        if discount_type == DiscountType.PERCENTAGE:
            discount_amount = _money(subtotal * discount_value / Decimal("100"))
        else:
            discount_amount = min(_money(discount_value), subtotal)
    total = _money(subtotal - discount_amount)

    payments = Decimal("0")
    refunds = Decimal("0")
    for tx, _invoice in tx_rows:
        if tx.direction == TransactionDirection.DEBIT:
            payments += _money(tx.amount)
        else:
            refunds += _money(tx.amount)
    paid = _money(payments - refunds)
    due = _money(max(total - paid, Decimal("0")))
    advance_balance = _money(max(paid - total, Decimal("0")))

    summary: dict[str, Any] = {
        "subtotal": f"{subtotal:.2f}",
        "discount_type": discount_type,
        "discount_value": f"{discount_value:.2f}" if discount_value is not None else None,
        "discount_amount": f"{discount_amount:.2f}",
        "total": f"{total:.2f}",
        "paid": f"{paid:.2f}",
        "due": f"{due:.2f}",
        "advance_balance": f"{advance_balance:.2f}",
    }

    entries.sort(key=lambda e: (e["entry_date"], e["created_at"]))
    return {"entries": entries, "summary": summary}


# ── Discount editor (FR-18.3, TODO-181) ────────────────────────────────────


async def set_project_discount(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    discount_type: DiscountType | None,
    discount_value: Decimal | None,
    actor_id: uuid.UUID,
) -> Project:
    """Replace (or clear) the project's single active discount.

    Audited with old/new values (project.discount_updated). Validation:
    None clears; percentage must be 0..100; fixed must be >= 0. Commits.
    """
    project = await _get_project(session, tenant_id, project_id)

    if discount_type is None:
        new_type: DiscountType | None = None
        new_value: Decimal | None = None
    elif discount_type == DiscountType.PERCENTAGE:
        if discount_value is None or not (Decimal("0") <= _money(discount_value) <= Decimal("100")):
            raise DiscountValidationError("Percentage discount must be between 0 and 100")
        new_type = discount_type
        new_value = _money(discount_value)
    else:
        if discount_value is None or _money(discount_value) < 0:
            raise DiscountValidationError("Fixed discount must be greater than or equal to 0")
        new_type = discount_type
        new_value = _money(discount_value)

    old_type = project.discount_type
    old_value = project.discount_value
    project.discount_type = new_type
    project.discount_value = new_value
    project.discount_updated_at = datetime.now(UTC)
    project.discount_updated_by = actor_id

    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="project.discount_updated",
        entity_type="project",
        entity_id=str(project.id),
        details={
            "old_type": old_type.value if old_type is not None else None,
            "old_value": f"{old_value:.2f}" if old_value is not None else None,
            "new_type": new_type.value if new_type is not None else None,
            "new_value": f"{new_value:.2f}" if new_value is not None else None,
        },
    )
    await session.commit()
    await session.refresh(project)
    return project
