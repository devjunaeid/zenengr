"""Company global ledger and operational analytics service (FEAT-025, TODO-213).

Provides tenant-scoped, batch-aggregated financial and operational metrics:
- Summary KPI cards across any date window.
- Month-wise / Day-wise timeline trends.
- Project-wise financial and services rollup.
- Client-wise billing, receivables, and advance balances.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, case, cast, func, literal, or_, select, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advance import Advance
from app.models.client import Client
from app.models.enums import (
    InvoiceStatus,
    LedgerEntryType,
    PaymentKind,
    TransactionDirection,
)
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.ledger_entry import LedgerEntry
from app.models.payment import Payment
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.transaction import PaymentAllocation, Transaction

_MONEY_STATUSES = [
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.PAID,
]


def _fmt(val: Decimal | int | float | None) -> str:
    """Format money value as a 2-decimal string."""
    if val is None:
        return "0.00"
    return f"{Decimal(val):.2f}"


def _clamp(val: Decimal) -> Decimal:
    """Clamp negative numbers to zero."""
    return val if val >= Decimal("0") else Decimal("0")


def _month_label(period_key: str) -> str:
    """Convert 'YYYY-MM' to human label like 'Sep 2026'."""
    try:
        parts = period_key.split("-")
        if len(parts) == 2:
            dt = datetime(int(parts[0]), int(parts[1]), 1)
            return dt.strftime("%b %Y")
        if len(parts) == 3:
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            return dt.strftime("%d %b %Y")
    except (ValueError, IndexError):
        return period_key
    return period_key


async def get_company_ledger(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    tag: str | None = None,
    granularity: str = "month",
    tab: str = "all",
) -> dict[str, Any]:
    """Compile organization-wide financial and operational reporting.

    Uses high-performance batch SQL aggregates with zero N+1 queries.
    """

    # ── 1. Unified Project Rollup (Ledger-derived single query) ─────────────
    # Computes authoritative billed, paid, and balance due per project from
    # ledger entries, attached services, project discounts, and payments.
    p_filter = [Project.tenant_id == tenant_id]
    if client_id:
        p_filter.append(Project.client_id == client_id)
    if project_id:
        p_filter.append(Project.id == project_id)
    clean_tag = tag.strip().lstrip("#") if tag and tag.strip() else None
    if clean_tag:
        p_filter.append(Client.tags.op("@>")(func.jsonb_build_array(clean_tag)))

    # 1a. Project ledger charges
    charge_sub = (
        select(
            LedgerEntry.project_id,
            func.coalesce(func.sum(LedgerEntry.amount), 0).label("charge_amt"),
            func.count(LedgerEntry.id).label("charge_cnt"),
        )
        .join(Project, LedgerEntry.project_id == Project.id)
        .where(
            Project.tenant_id == tenant_id,
            LedgerEntry.type == LedgerEntryType.CHARGE,
            LedgerEntry.voided_at.is_(None),
        )
        .group_by(LedgerEntry.project_id)
        .cte("p_charge_sub")
    )

    # 1b. Project direct payments & refunds from unified Payment table
    pay_sub = (
        select(
            Payment.project_id,
            func.coalesce(
                func.sum(
                    case(
                        (Payment.kind == PaymentKind.RECEIPT, Payment.amount),
                        (Payment.kind == PaymentKind.REFUND, -Payment.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("paid_amt"),
        )
        .where(
            Payment.tenant_id == tenant_id,
            Payment.voided_at.is_(None),
        )
        .group_by(Payment.project_id)
        .cte("p_pay_sub")
    )

    # 1b-2. Legacy unmigrated direct LedgerEntry payments/refunds
    leg_pay_sub = (
        select(
            LedgerEntry.project_id,
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.type == LedgerEntryType.PAYMENT, LedgerEntry.amount),
                        (LedgerEntry.type == LedgerEntryType.REFUND, -LedgerEntry.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("leg_paid"),
        )
        .where(
            LedgerEntry.source_id.is_(None),
            LedgerEntry.voided_at.is_(None),
            LedgerEntry.type.in_([LedgerEntryType.PAYMENT, LedgerEntryType.REFUND]),
        )
        .group_by(LedgerEntry.project_id)
        .cte("p_leg_pay_sub")
    )

    # 1c. Payment transactions on project invoices
    tx_sub = (
        select(
            Invoice.project_id,
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.direction == TransactionDirection.DEBIT, Transaction.amount),
                        (Transaction.direction == TransactionDirection.CREDIT, -Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("net_tx"),
        )
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .outerjoin(Payment, Transaction.payment_id == Payment.id)
        .where(
            Invoice.tenant_id == tenant_id,
            or_(Invoice.status.in_(_MONEY_STATUSES), Invoice.is_auto.is_(True)),
            Invoice.status != InvoiceStatus.VOID,
            or_(
                Transaction.payment_id.is_(None),
                Payment.project_id.is_(None),
            ),
            Transaction.voided_at.is_(None),
        )
        .group_by(Invoice.project_id)
        .cte("p_tx_sub")
    )

    # 1d. Legacy unmigrated advance allocations on project invoices
    adv_alloc_sub = (
        select(
            Invoice.project_id,
            func.coalesce(func.sum(PaymentAllocation.amount), 0).label("adv_allocated"),
        )
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
            PaymentAllocation.payment_id.is_(None),
            PaymentAllocation.transaction_id.is_(None),
            PaymentAllocation.advance_id.is_not(None),
            PaymentAllocation.voided_at.is_(None),
        )
        .group_by(Invoice.project_id)
        .cte("p_adv_alloc_sub")
    )

    # 1e. Attached services count & value (used as fallback when no ledger entries exist)
    svc_sub = (
        select(
            ProjectService.project_id,
            func.count(ProjectService.id).label("svc_cnt"),
            func.coalesce(func.sum(ProjectService.price_at_attachment), 0).label("svc_val"),
        )
        .join(Project, ProjectService.project_id == Project.id)
        .where(Project.tenant_id == tenant_id)
        .group_by(ProjectService.project_id)
        .cte("p_svc_sub")
    )

    # 1f. Custom line items on non-auto invoices
    custom_sub = (
        select(
            Invoice.project_id,
            func.coalesce(func.sum(InvoiceLineItem.amount), 0).label("custom_val"),
        )
        .join(InvoiceLineItem, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status != InvoiceStatus.DRAFT,
            Invoice.is_auto.is_(False),
            InvoiceLineItem.project_service_id.is_(None),
        )
        .group_by(Invoice.project_id)
        .cte("p_custom_sub")
    )

    p_stmt = (
        select(
            Project.id,
            Project.name,
            Project.client_id,
            Project.status,
            Project.created_at,
            Project.discount_type,
            Project.discount_value,
            func.coalesce(Client.name, "").label("client_name"),
            func.coalesce(Client.tags, text("'[]'::jsonb")).label("client_tags"),
            func.coalesce(charge_sub.c.charge_amt, 0).label("charge_amt"),
            func.coalesce(charge_sub.c.charge_cnt, 0).label("charge_cnt"),
            (
                func.coalesce(pay_sub.c.paid_amt, 0)
                + func.coalesce(leg_pay_sub.c.leg_paid, 0)
            ).label("direct_paid"),
            func.coalesce(tx_sub.c.net_tx, 0).label("net_tx"),
            func.coalesce(adv_alloc_sub.c.adv_allocated, 0).label("adv_allocated"),
            func.coalesce(svc_sub.c.svc_cnt, 0).label("services_count"),
            func.coalesce(svc_sub.c.svc_val, 0).label("services_value"),
            func.coalesce(custom_sub.c.custom_val, 0).label("custom_val"),
        )
        .outerjoin(Client, Project.client_id == Client.id)
        .outerjoin(charge_sub, Project.id == charge_sub.c.project_id)
        .outerjoin(pay_sub, Project.id == pay_sub.c.project_id)
        .outerjoin(leg_pay_sub, Project.id == leg_pay_sub.c.project_id)
        .outerjoin(tx_sub, Project.id == tx_sub.c.project_id)
        .outerjoin(adv_alloc_sub, Project.id == adv_alloc_sub.c.project_id)
        .outerjoin(svc_sub, Project.id == svc_sub.c.project_id)
        .outerjoin(custom_sub, Project.id == custom_sub.c.project_id)
        .where(*p_filter)
        .order_by(Project.created_at.desc())
    )

    proj_rows = (await session.execute(p_stmt)).all()

    # Process project rows
    projects_list: list[dict[str, Any]] = []
    projects_by_client: dict[uuid.UUID, list[dict[str, Any]]] = {}
    lifetime_billed_acc = Decimal("0")
    lifetime_paid_acc = Decimal("0")
    lifetime_due_acc = Decimal("0")

    for p in proj_rows:
        raw_charges = Decimal(p.charge_amt) if p.charge_cnt > 0 else Decimal(p.services_value)
        raw_subtotal = raw_charges + Decimal(p.custom_val)

        # Apply project discount
        if p.discount_type and p.discount_value:
            d_type = getattr(p.discount_type, "value", str(p.discount_type))
            if d_type == "fixed":
                raw_subtotal = _clamp(raw_subtotal - Decimal(p.discount_value))
            elif d_type == "percentage":
                disc = (raw_subtotal * Decimal(p.discount_value) / Decimal("100")).quantize(
                    Decimal("0.01")
                )
                raw_subtotal = _clamp(raw_subtotal - disc)

        p_billed = raw_subtotal
        p_paid = _clamp(Decimal(p.direct_paid) + Decimal(p.net_tx) + Decimal(p.adv_allocated))
        p_due = _clamp(p_billed - p_paid)

        lifetime_billed_acc += p_billed
        lifetime_paid_acc += p_paid
        lifetime_due_acc += p_due
        p_dict = {
            "project_id": p.id,
            "short_id": str(p.id)[:6].upper(),
            "name": p.name,
            "client_id": p.client_id,
            "client_name": p.client_name,
            "client_tags": p.client_tags or [],
            "status": p.status.value if hasattr(p.status, "value") else str(p.status),
            "created_at": p.created_at,
            "services_count": int(p.services_count),
            "total_value": _fmt(p_billed),
            "total_invoiced": _fmt(p_billed),
            "total_paid": _fmt(p_paid),
            "balance_due": _fmt(p_due),
            "_billed_dec": p_billed,
            "_paid_dec": p_paid,
            "_due_dec": p_due,
        }
        projects_list.append(p_dict)
        if p.client_id:
            projects_by_client.setdefault(p.client_id, []).append(p_dict)

    # ── 1g. Individual / General Invoices (not connected to a project) ─────
    # For invoices where Invoice.project_id IS NULL, finances are derived
    # directly from the invoice records and their transactions.
    gen_lifetime_billed = Decimal("0")
    gen_lifetime_paid = Decimal("0")
    gen_lifetime_due = Decimal("0")
    gen_range_billed = Decimal("0")
    gen_range_paid_fallback = Decimal("0")

    if not project_id and not client_id and not clean_tag:
        gen_tx_sub = (
            select(
                Transaction.invoice_id,
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.direction == TransactionDirection.DEBIT,
                                Transaction.amount,
                            ),
                            (
                                Transaction.direction == TransactionDirection.CREDIT,
                                -Transaction.amount,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("net_tx"),
            )
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.project_id.is_(None),
                Invoice.status.in_(_MONEY_STATUSES),
                Transaction.voided_at.is_(None),
            )
            .group_by(Transaction.invoice_id)
            .cte("gen_tx_sub")
        )

        gen_adv_sub = (
            select(
                InvoiceLineItem.invoice_id,
                func.coalesce(func.sum(PaymentAllocation.amount), 0).label("adv_amt"),
            )
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .join(PaymentAllocation, PaymentAllocation.line_item_id == InvoiceLineItem.id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.project_id.is_(None),
                Invoice.status.in_(_MONEY_STATUSES),
                PaymentAllocation.transaction_id.is_(None),
                PaymentAllocation.advance_id.is_not(None),
                PaymentAllocation.voided_at.is_(None),
            )
            .group_by(InvoiceLineItem.invoice_id)
            .cte("gen_adv_sub")
        )

        effective_date_col = func.coalesce(Invoice.issue_date, cast(Invoice.created_at, Date))
        gen_stmt = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.status,
                Invoice.total,
                effective_date_col.label("effective_date"),
                func.coalesce(gen_tx_sub.c.net_tx, 0).label("tx_paid"),
                func.coalesce(gen_adv_sub.c.adv_amt, 0).label("adv_paid"),
            )
            .outerjoin(gen_tx_sub, Invoice.id == gen_tx_sub.c.invoice_id)
            .outerjoin(gen_adv_sub, Invoice.id == gen_adv_sub.c.invoice_id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.project_id.is_(None),
                Invoice.status.in_(_MONEY_STATUSES),
            )
        )
        gen_rows = (await session.execute(gen_stmt)).all()

        for gi in gen_rows:
            gi_billed = Decimal(gi.total or 0)
            gi_recorded = Decimal(gi.tx_paid or 0) + Decimal(gi.adv_paid or 0)
            if gi.status == InvoiceStatus.PAID:
                gi_paid = max(gi_billed, gi_recorded)
                gi_due = Decimal("0")
            else:
                gi_paid = _clamp(gi_recorded)
                gi_due = _clamp(gi_billed - gi_paid)

            gen_lifetime_billed += gi_billed
            gen_lifetime_paid += gi_paid
            gen_lifetime_due += gi_due

            if date_from or date_to:
                eff = gi.effective_date
                in_range = True
                if date_from and eff < date_from:
                    in_range = False
                if date_to and eff > date_to:
                    in_range = False
                if in_range:
                    gen_range_billed += gi_billed
                    if gi.status == InvoiceStatus.PAID and gi_recorded == Decimal("0"):
                        gen_range_paid_fallback += gi_billed

        # Incorporate non-project individual invoices into cumulative lifetime totals
        lifetime_billed_acc += gen_lifetime_billed
        lifetime_paid_acc += gen_lifetime_paid
        lifetime_due_acc += gen_lifetime_due

    # ── 2. Executive Summary Metrics ────────────────────────────────────────
    # New projects count in range
    proj_q = select(func.count(Project.id)).where(Project.tenant_id == tenant_id)
    if client_id:
        proj_q = proj_q.where(Project.client_id == client_id)
    if project_id:
        proj_q = proj_q.where(Project.id == project_id)
    if date_from:
        proj_q = proj_q.where(cast(Project.created_at, Date) >= date_from)
    if date_to:
        proj_q = proj_q.where(cast(Project.created_at, Date) <= date_to)

    # New clients count in range
    cli_q = select(func.count(Client.id)).where(Client.tenant_id == tenant_id)
    if client_id:
        cli_q = cli_q.where(Client.id == client_id)
    elif project_id:
        proj_cli_sub = select(Project.client_id).where(Project.id == project_id).scalar_subquery()
        cli_q = cli_q.where(Client.id == proj_cli_sub)
    if date_from:
        cli_q = cli_q.where(cast(Client.created_at, Date) >= date_from)
    if date_to:
        cli_q = cli_q.where(cast(Client.created_at, Date) <= date_to)

    # New services count & value in range
    svc_q = (
        select(
            func.count(ProjectService.id).label("cnt"),
            func.coalesce(func.sum(ProjectService.price_at_attachment), 0).label("val"),
        )
        .join(Project, ProjectService.project_id == Project.id)
        .where(Project.tenant_id == tenant_id)
    )
    if client_id:
        svc_q = svc_q.where(Project.client_id == client_id)
    if project_id:
        svc_q = svc_q.where(Project.id == project_id)
    if date_from:
        svc_q = svc_q.where(cast(ProjectService.created_at, Date) >= date_from)
    if date_to:
        svc_q = svc_q.where(cast(ProjectService.created_at, Date) <= date_to)

    # Charges in range: LedgerEntry charges
    charge_date_col = func.coalesce(LedgerEntry.entry_date, cast(LedgerEntry.created_at, Date))
    charge_range_q = (
        select(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .join(Project, LedgerEntry.project_id == Project.id)
        .where(
            Project.tenant_id == tenant_id,
            LedgerEntry.type == LedgerEntryType.CHARGE,
            LedgerEntry.voided_at.is_(None),
        )
    )
    if project_id:
        charge_range_q = charge_range_q.where(Project.id == project_id)
    elif client_id:
        charge_range_q = charge_range_q.where(Project.client_id == client_id)
    if date_from:
        charge_range_q = charge_range_q.where(charge_date_col >= date_from)
    if date_to:
        charge_range_q = charge_range_q.where(charge_date_col <= date_to)

    # Fallback charges in range for projects without ledger entries
    proj_with_ledger_charges = (
        select(LedgerEntry.project_id)
        .join(Project, LedgerEntry.project_id == Project.id)
        .where(
            Project.tenant_id == tenant_id,
            LedgerEntry.type == LedgerEntryType.CHARGE,
            LedgerEntry.voided_at.is_(None),
        )
        .distinct()
        .scalar_subquery()
    )
    ps_fallback_range_q = (
        select(func.coalesce(func.sum(ProjectService.price_at_attachment), 0))
        .join(Project, ProjectService.project_id == Project.id)
        .where(
            Project.tenant_id == tenant_id,
            Project.id.not_in(proj_with_ledger_charges),
        )
    )
    if project_id:
        ps_fallback_range_q = ps_fallback_range_q.where(Project.id == project_id)
    elif client_id:
        ps_fallback_range_q = ps_fallback_range_q.where(Project.client_id == client_id)
    if date_from:
        ps_fallback_range_q = ps_fallback_range_q.where(
            cast(ProjectService.created_at, Date) >= date_from
        )
    if date_to:
        ps_fallback_range_q = ps_fallback_range_q.where(
            cast(ProjectService.created_at, Date) <= date_to
        )

    # Collections in range: unified Payment table
    pay_range_q = select(
        func.coalesce(
            func.sum(
                case(
                    (Payment.kind == PaymentKind.RECEIPT, Payment.amount),
                    (Payment.kind == PaymentKind.REFUND, -Payment.amount),
                    else_=0,
                )
            ),
            0,
        )
    ).where(
        Payment.tenant_id == tenant_id,
        Payment.voided_at.is_(None),
    )
    if project_id:
        pay_range_q = pay_range_q.where(Payment.project_id == project_id)
    elif client_id:
        pay_range_q = pay_range_q.where(Payment.client_id == client_id)
    if date_from:
        pay_range_q = pay_range_q.where(Payment.paid_on >= date_from)
    if date_to:
        pay_range_q = pay_range_q.where(Payment.paid_on <= date_to)

    # Legacy unmigrated transaction collections fallback
    tx_legacy_range_q = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.direction == TransactionDirection.DEBIT, Transaction.amount),
                        (Transaction.direction == TransactionDirection.CREDIT, -Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            )
        )
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
            Transaction.payment_id.is_(None),
            Transaction.voided_at.is_(None),
        )
    )
    if project_id:
        tx_legacy_range_q = tx_legacy_range_q.where(Invoice.project_id == project_id)
    elif client_id:
        tx_legacy_range_q = tx_legacy_range_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        tx_legacy_range_q = tx_legacy_range_q.where(
            cast(Transaction.recorded_at, Date) >= date_from
        )
    if date_to:
        tx_legacy_range_q = tx_legacy_range_q.where(cast(Transaction.recorded_at, Date) <= date_to)

    # Advances
    adv_q = select(func.coalesce(func.sum(Advance.remaining_amount), 0)).where(
        Advance.tenant_id == tenant_id,
        Advance.remaining_amount > Decimal("0"),
    )
    if client_id:
        adv_q = adv_q.where(Advance.client_id == client_id)
    elif project_id:
        p_cli_sub = select(Project.client_id).where(Project.id == project_id).scalar_subquery()
        adv_q = adv_q.where(Advance.client_id == p_cli_sub)

    summary_stmt = select(
        proj_q.scalar_subquery().label("new_projects"),
        cli_q.scalar_subquery().label("new_clients"),
        select(svc_q.subquery().c.cnt).scalar_subquery().label("new_services"),
        select(svc_q.subquery().c.val).scalar_subquery().label("new_services_val"),
        charge_range_q.scalar_subquery().label("charge_range"),
        ps_fallback_range_q.scalar_subquery().label("ps_fallback_range"),
        pay_range_q.scalar_subquery().label("payment_range"),
        tx_legacy_range_q.scalar_subquery().label("tx_legacy_range"),
        adv_q.scalar_subquery().label("advances"),
    )
    s_row = (await session.execute(summary_stmt)).one()

    new_projects_count = int(s_row.new_projects or 0)
    new_clients_count = int(s_row.new_clients or 0)
    new_services_count = int(s_row.new_services or 0)
    new_services_value = Decimal(s_row.new_services_val or 0)

    # If date range is filtered, show billed charges in range; otherwise lifetime billed
    if date_from or date_to:
        total_billed_in_range = (
            Decimal(s_row.charge_range or 0)
            + Decimal(s_row.ps_fallback_range or 0)
            + gen_range_billed
        )
        net_collected_in_range = _clamp(
            Decimal(s_row.payment_range or 0)
            + Decimal(s_row.tx_legacy_range or 0)
            + gen_range_paid_fallback
        )
    else:
        total_billed_in_range = lifetime_billed_acc
        net_collected_in_range = lifetime_paid_acc

    total_advance_balance = Decimal(s_row.advances or 0)

    summary = {
        "period_from": date_from,
        "period_to": date_to,
        "new_projects_count": new_projects_count,
        "new_clients_count": new_clients_count,
        "new_services_count": new_services_count,
        "new_services_value": _fmt(new_services_value),
        "total_invoiced": _fmt(total_billed_in_range),
        "total_collected": _fmt(net_collected_in_range),
        "total_due": _fmt(lifetime_due_acc),
        "total_advance_balance": _fmt(total_advance_balance),
    }

    # ── 3. Unified Timeline Series (Single Query Union) ──────────────────────
    timeline: list[dict[str, Any]] = []
    if tab in ("all", "timeline"):
        time_fmt = "YYYY-MM" if granularity == "month" else "YYYY-MM-DD"

        # 1a. Charges from LedgerEntry
        q1a = (
            select(
                func.to_char(charge_date_col, time_fmt).label("p"),
                literal("charge").label("kind"),
                func.coalesce(func.sum(LedgerEntry.amount), 0).label("num1"),
                literal(0).label("num2"),
            )
            .join(Project, LedgerEntry.project_id == Project.id)
            .where(
                Project.tenant_id == tenant_id,
                LedgerEntry.type == LedgerEntryType.CHARGE,
                LedgerEntry.voided_at.is_(None),
            )
        )
        if project_id:
            q1a = q1a.where(Project.id == project_id)
        elif client_id:
            q1a = q1a.where(Project.client_id == client_id)
        if date_from:
            q1a = q1a.where(charge_date_col >= date_from)
        if date_to:
            q1a = q1a.where(charge_date_col <= date_to)
        q1a = q1a.group_by("p")

        # 1b. Fallback charges for projects without ledger entries
        svc_date_col = cast(ProjectService.created_at, Date)
        q1b = (
            select(
                func.to_char(svc_date_col, time_fmt).label("p"),
                literal("charge").label("kind"),
                func.coalesce(func.sum(ProjectService.price_at_attachment), 0).label("num1"),
                literal(0).label("num2"),
            )
            .join(Project, ProjectService.project_id == Project.id)
            .where(
                Project.tenant_id == tenant_id,
                Project.id.not_in(proj_with_ledger_charges),
            )
        )
        if project_id:
            q1b = q1b.where(Project.id == project_id)
        elif client_id:
            q1b = q1b.where(Project.client_id == client_id)
        if date_from:
            q1b = q1b.where(svc_date_col >= date_from)
        if date_to:
            q1b = q1b.where(svc_date_col <= date_to)
        q1b = q1b.group_by("p")

        # 2a. Unified Payments
        pay_date_col = func.coalesce(Payment.paid_on, cast(Payment.created_at, Date))
        q2a = select(
            func.to_char(pay_date_col, time_fmt).label("p"),
            literal("tx").label("kind"),
            func.coalesce(func.sum(Payment.amount), 0).label("num1"),
            case(
                (Payment.kind == PaymentKind.RECEIPT, 1),
                (Payment.kind == PaymentKind.REFUND, -1),
                else_=0,
            ).label("num2"),
        ).where(
            Payment.tenant_id == tenant_id,
            Payment.voided_at.is_(None),
        )
        if project_id:
            q2a = q2a.where(Payment.project_id == project_id)
        elif client_id:
            q2a = q2a.where(Payment.client_id == client_id)
        if date_from:
            q2a = q2a.where(pay_date_col >= date_from)
        if date_to:
            q2a = q2a.where(pay_date_col <= date_to)
        q2a = q2a.group_by("p", "num2")

        # 2b. Legacy Unmigrated Transactions
        q2b = (
            select(
                func.to_char(cast(Transaction.recorded_at, Date), time_fmt).label("p"),
                literal("tx").label("kind"),
                func.coalesce(func.sum(Transaction.amount), 0).label("num1"),
                case(
                    (Transaction.direction == TransactionDirection.DEBIT, 1),
                    (Transaction.direction == TransactionDirection.CREDIT, -1),
                    else_=0,
                ).label("num2"),
            )
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(_MONEY_STATUSES),
                Transaction.payment_id.is_(None),
                Transaction.voided_at.is_(None),
            )
        )
        if project_id:
            q2b = q2b.where(Invoice.project_id == project_id)
        elif client_id:
            q2b = q2b.join(Project, Invoice.project_id == Project.id).where(
                Project.client_id == client_id
            )
        if date_from:
            q2b = q2b.where(cast(Transaction.recorded_at, Date) >= date_from)
        if date_to:
            q2b = q2b.where(cast(Transaction.recorded_at, Date) <= date_to)
        q2b = q2b.group_by("p", "num2")

        # 3. Projects
        q3 = select(
            func.to_char(cast(Project.created_at, Date), time_fmt).label("p"),
            literal("proj").label("kind"),
            func.count(Project.id).label("num1"),
            literal(0).label("num2"),
        ).where(Project.tenant_id == tenant_id)
        if client_id:
            q3 = q3.where(Project.client_id == client_id)
        if project_id:
            q3 = q3.where(Project.id == project_id)
        if date_from:
            q3 = q3.where(cast(Project.created_at, Date) >= date_from)
        if date_to:
            q3 = q3.where(cast(Project.created_at, Date) <= date_to)
        q3 = q3.group_by("p")

        # 4. Clients (only if not project_id)
        if not project_id:
            q4 = select(
                func.to_char(cast(Client.created_at, Date), time_fmt).label("p"),
                literal("client").label("kind"),
                func.count(Client.id).label("num1"),
                literal(0).label("num2"),
            ).where(Client.tenant_id == tenant_id)
            if client_id:
                q4 = q4.where(Client.id == client_id)
            if date_from:
                q4 = q4.where(cast(Client.created_at, Date) >= date_from)
            if date_to:
                q4 = q4.where(cast(Client.created_at, Date) <= date_to)
            q4 = q4.group_by("p")
        else:
            q4 = None

        # 5. Services
        q5 = (
            select(
                func.to_char(cast(ProjectService.created_at, Date), time_fmt).label("p"),
                literal("svc").label("kind"),
                func.count(ProjectService.id).label("num1"),
                literal(0).label("num2"),
            )
            .join(Project, ProjectService.project_id == Project.id)
            .where(Project.tenant_id == tenant_id)
        )
        if client_id:
            q5 = q5.where(Project.client_id == client_id)
        if project_id:
            q5 = q5.where(Project.id == project_id)
        if date_from:
            q5 = q5.where(cast(ProjectService.created_at, Date) >= date_from)
        if date_to:
            q5 = q5.where(cast(ProjectService.created_at, Date) <= date_to)
        q5 = q5.group_by("p")

        # 6. General (non-project) invoices as charges
        if not project_id and not client_id and not clean_tag:
            inv_date_col = func.coalesce(Invoice.issue_date, cast(Invoice.created_at, Date))
            q6 = (
                select(
                    func.to_char(inv_date_col, time_fmt).label("p"),
                    literal("charge").label("kind"),
                    func.coalesce(func.sum(Invoice.total), 0).label("num1"),
                    literal(0).label("num2"),
                )
                .where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.project_id.is_(None),
                    Invoice.status.in_(_MONEY_STATUSES),
                )
            )
            if date_from:
                q6 = q6.where(inv_date_col >= date_from)
            if date_to:
                q6 = q6.where(inv_date_col <= date_to)
            q6 = q6.group_by("p")
        else:
            q6 = None

        all_queries = [q1a, q1b, q2a, q2b, q3, q5]
        if q4 is not None:
            all_queries.append(q4)
        if q6 is not None:
            all_queries.append(q6)

        u = union_all(*all_queries).subquery()
        timeline_rows = (await session.execute(select(u.c.p, u.c.kind, u.c.num1, u.c.num2))).all()

        timeline_dict: dict[str, dict[str, Any]] = {}
        for p, kind, n1, n2 in timeline_rows:
            if not p:
                continue
            if p not in timeline_dict:
                timeline_dict[p] = {
                    "period": p,
                    "period_label": _month_label(p),
                    "new_projects": 0,
                    "new_clients": 0,
                    "new_services": 0,
                    "invoiced_dec": Decimal("0"),
                    "collected_dec": Decimal("0"),
                }
            b = timeline_dict[p]
            if kind == "charge":
                b["invoiced_dec"] += Decimal(n1)
            elif kind == "tx":
                amt = Decimal(n1)
                if n2 == 1:
                    b["collected_dec"] += amt
                elif n2 == -1:
                    b["collected_dec"] -= amt
            elif kind == "proj":
                b["new_projects"] += int(n1)
            elif kind == "client":
                b["new_clients"] += int(n1)
            elif kind == "svc":
                b["new_services"] += int(n1)

        for k in sorted(timeline_dict.keys(), reverse=True):
            item = timeline_dict[k]
            coll = _clamp(item["collected_dec"])
            inv = item["invoiced_dec"]
            net_change = inv - coll
            timeline.append(
                {
                    "period": item["period"],
                    "period_label": item["period_label"],
                    "new_projects": item["new_projects"],
                    "new_clients": item["new_clients"],
                    "new_services": item["new_services"],
                    "invoiced_amount": _fmt(inv),
                    "collected_amount": _fmt(coll),
                    "net_due_change": _fmt(net_change),
                }
            )

    # ── 4. Unified Client Rollup (Aggregated from Project Ledgers) ───────────
    clients_list: list[dict[str, Any]] = []
    if tab in ("all", "clients"):
        c_filter = [Client.tenant_id == tenant_id]
        if client_id:
            c_filter.append(Client.id == client_id)
        elif project_id:
            c_filter.append(
                Client.id
                == select(Project.client_id).where(Project.id == project_id).scalar_subquery()
            )

        # Advances per client
        cadv_sub = (
            select(
                Advance.client_id,
                func.coalesce(func.sum(Advance.remaining_amount), 0).label("advances"),
            )
            .where(Advance.tenant_id == tenant_id, Advance.remaining_amount > Decimal("0"))
            .group_by(Advance.client_id)
        )
        cadv_rows = (await session.execute(cadv_sub)).all()
        adv_map: dict[uuid.UUID, Decimal] = {
            row.client_id: Decimal(row.advances) for row in cadv_rows
        }

        c_stmt = (
            select(
                Client.id,
                Client.name,
                Client.client_type,
                Client.created_at,
            )
            .where(*c_filter)
            .order_by(Client.name.asc())
        )
        client_rows = (await session.execute(c_stmt)).all()

        for c in client_rows:
            c_projs = projects_by_client.get(c.id, [])
            c_active_projects = len(c_projs)
            c_services_cnt = sum(p["services_count"] for p in c_projs)
            c_billed = sum((p["_billed_dec"] for p in c_projs), Decimal("0"))
            c_paid = sum((p["_paid_dec"] for p in c_projs), Decimal("0"))
            c_due = sum((p["_due_dec"] for p in c_projs), Decimal("0"))
            c_advance = adv_map.get(c.id, Decimal("0"))

            clients_list.append(
                {
                    "client_id": c.id,
                    "name": c.name,
                    "client_type": c.client_type.value
                    if hasattr(c.client_type, "value")
                    else str(c.client_type),
                    "created_at": c.created_at,
                    "active_projects_count": c_active_projects,
                    "total_services_count": c_services_cnt,
                    "total_invoiced": _fmt(c_billed),
                    "total_paid": _fmt(c_paid),
                    "total_due": _fmt(c_due),
                    "advance_balance": _fmt(c_advance),
                }
            )

    # Strip temporary calculation keys from projects_list
    final_projects_list = []
    if tab in ("all", "projects"):
        for p in projects_list:
            final_projects_list.append({k: v for k, v in p.items() if not k.startswith("_")})

    return {
        "summary": summary,
        "timeline": timeline,
        "projects": final_projects_list,
        "clients": clients_list,
        "filters_applied": {
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "client_id": str(client_id) if client_id else None,
            "project_id": str(project_id) if project_id else None,
            "tag": tag,
            "granularity": granularity,
            "tab": tab,
        },
    }
