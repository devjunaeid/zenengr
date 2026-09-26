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

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.advance import Advance
from app.models.client import Client
from app.models.enums import InvoiceStatus, TransactionDirection
from app.models.invoice import Invoice, InvoiceLineItem
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
    granularity: str = "month",
) -> dict[str, Any]:
    """Compile organization-wide financial and operational reporting.

    Uses efficient batch SQL aggregates with zero N+1 queries.
    """
    # ── 1. Summary: New Projects in range ─────────────────────────────────────
    proj_stmt = select(func.count(Project.id)).where(Project.tenant_id == tenant_id)
    if client_id:
        proj_stmt = proj_stmt.where(Project.client_id == client_id)
    if project_id:
        proj_stmt = proj_stmt.where(Project.id == project_id)
    if date_from:
        proj_stmt = proj_stmt.where(cast(Project.created_at, Date) >= date_from)
    if date_to:
        proj_stmt = proj_stmt.where(cast(Project.created_at, Date) <= date_to)
    new_projects_count = int((await session.execute(proj_stmt)).scalar_one() or 0)

    # ── 2. Summary: New Clients in range ──────────────────────────────────────
    cli_stmt = select(func.count(Client.id)).where(Client.tenant_id == tenant_id)
    if client_id:
        cli_stmt = cli_stmt.where(Client.id == client_id)
    if date_from:
        cli_stmt = cli_stmt.where(cast(Client.created_at, Date) >= date_from)
    if date_to:
        cli_stmt = cli_stmt.where(cast(Client.created_at, Date) <= date_to)
    new_clients_count = int((await session.execute(cli_stmt)).scalar_one() or 0)

    # ── 3. Summary: New Services in range ─────────────────────────────────────
    svc_stmt = (
        select(
            func.count(ProjectService.id),
            func.coalesce(func.sum(ProjectService.price_at_attachment), 0),
        )
        .join(Project, ProjectService.project_id == Project.id)
        .where(Project.tenant_id == tenant_id)
    )
    if client_id:
        svc_stmt = svc_stmt.where(Project.client_id == client_id)
    if project_id:
        svc_stmt = svc_stmt.where(Project.id == project_id)
    if date_from:
        svc_stmt = svc_stmt.where(cast(ProjectService.created_at, Date) >= date_from)
    if date_to:
        svc_stmt = svc_stmt.where(cast(ProjectService.created_at, Date) <= date_to)
    svc_res = (await session.execute(svc_stmt)).one()
    new_services_count = int(svc_res[0] or 0)
    new_services_value = Decimal(svc_res[1] or 0)

    # ── 4. Summary: Invoicing in range ────────────────────────────────────────
    inv_date_col = func.coalesce(Invoice.issue_date, cast(Invoice.created_at, Date))
    inv_stmt = select(func.coalesce(func.sum(Invoice.total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.status.in_(_MONEY_STATUSES),
    )
    if project_id:
        inv_stmt = inv_stmt.where(Invoice.project_id == project_id)
    elif client_id:
        inv_stmt = inv_stmt.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        inv_stmt = inv_stmt.where(inv_date_col >= date_from)
    if date_to:
        inv_stmt = inv_stmt.where(inv_date_col <= date_to)
    total_invoiced_in_range = Decimal((await session.execute(inv_stmt)).scalar_one() or 0)

    # ── 5. Summary: Collections & Refunds in range ────────────────────────────
    tx_base = (
        select(
            Transaction.direction,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
    )
    if project_id:
        tx_base = tx_base.where(Invoice.project_id == project_id)
    elif client_id:
        tx_base = tx_base.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        tx_base = tx_base.where(cast(Transaction.recorded_at, Date) >= date_from)
    if date_to:
        tx_base = tx_base.where(cast(Transaction.recorded_at, Date) <= date_to)
    tx_rows = (await session.execute(tx_base.group_by(Transaction.direction))).all()

    collected_debits = Decimal("0")
    refund_credits = Decimal("0")
    for direction, amt in tx_rows:
        if direction == TransactionDirection.DEBIT:
            collected_debits += Decimal(amt)
        elif direction == TransactionDirection.CREDIT:
            refund_credits += Decimal(amt)
    net_collected_in_range = _clamp(collected_debits - refund_credits)

    # ── 6. Advances & Total Receivables ───────────────────────────────────────
    adv_stmt = select(func.coalesce(func.sum(Advance.remaining_amount), 0)).where(
        Advance.tenant_id == tenant_id,
        Advance.remaining_amount > Decimal("0"),
    )
    if client_id:
        adv_stmt = adv_stmt.where(Advance.client_id == client_id)
    total_advance_balance = Decimal((await session.execute(adv_stmt)).scalar_one() or 0)

    # Total lifetime invoiced & paid for receivables calculation
    tot_inv_q = select(func.coalesce(func.sum(Invoice.total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.status.in_(_MONEY_STATUSES),
    )
    if project_id:
        tot_inv_q = tot_inv_q.where(Invoice.project_id == project_id)
    elif client_id:
        tot_inv_q = tot_inv_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    lifetime_invoiced = Decimal((await session.execute(tot_inv_q)).scalar_one() or 0)

    alloc_q = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
    )
    if project_id:
        alloc_q = alloc_q.where(Invoice.project_id == project_id)
    elif client_id:
        alloc_q = alloc_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    lifetime_allocations = Decimal((await session.execute(alloc_q)).scalar_one() or 0)

    ref_q = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
            Transaction.direction == TransactionDirection.CREDIT,
        )
    )
    if project_id:
        ref_q = ref_q.where(Invoice.project_id == project_id)
    elif client_id:
        ref_q = ref_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    lifetime_refunds = Decimal((await session.execute(ref_q)).scalar_one() or 0)
    lifetime_paid = _clamp(lifetime_allocations - lifetime_refunds)
    total_due = _clamp(lifetime_invoiced - lifetime_paid)

    summary = {
        "period_from": date_from,
        "period_to": date_to,
        "new_projects_count": new_projects_count,
        "new_clients_count": new_clients_count,
        "new_services_count": new_services_count,
        "new_services_value": _fmt(new_services_value),
        "total_invoiced": _fmt(total_invoiced_in_range),
        "total_collected": _fmt(net_collected_in_range),
        "total_due": _fmt(total_due),
        "total_advance_balance": _fmt(total_advance_balance),
    }

    # ── 7. Timeline Series (Chronological Bucketing) ──────────────────────────
    time_fmt = "YYYY-MM" if granularity == "month" else "YYYY-MM-DD"
    timeline_dict: dict[str, dict[str, Any]] = {}

    def _ensure_bucket(key: str) -> dict[str, Any]:
        if key not in timeline_dict:
            timeline_dict[key] = {
                "period": key,
                "period_label": _month_label(key),
                "new_projects": 0,
                "new_clients": 0,
                "new_services": 0,
                "invoiced_dec": Decimal("0"),
                "collected_dec": Decimal("0"),
            }
        return timeline_dict[key]

    # Invoicing by bucket
    inv_t_stmt = (
        select(
            func.to_char(inv_date_col, time_fmt).label("p"),
            func.coalesce(func.sum(Invoice.total), 0),
        )
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
        .group_by("p")
    )
    if project_id:
        inv_t_stmt = inv_t_stmt.where(Invoice.project_id == project_id)
    elif client_id:
        inv_t_stmt = inv_t_stmt.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        inv_t_stmt = inv_t_stmt.where(inv_date_col >= date_from)
    if date_to:
        inv_t_stmt = inv_t_stmt.where(inv_date_col <= date_to)
    for p, amt in (await session.execute(inv_t_stmt)).all():
        if p:
            _ensure_bucket(p)["invoiced_dec"] += Decimal(amt)

    # Collections by bucket
    tx_t_stmt = (
        select(
            func.to_char(cast(Transaction.recorded_at, Date), time_fmt).label("p"),
            Transaction.direction,
            func.coalesce(func.sum(Transaction.amount), 0),
        )
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
        .group_by("p", Transaction.direction)
    )
    if project_id:
        tx_t_stmt = tx_t_stmt.where(Invoice.project_id == project_id)
    elif client_id:
        tx_t_stmt = tx_t_stmt.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        tx_t_stmt = tx_t_stmt.where(cast(Transaction.recorded_at, Date) >= date_from)
    if date_to:
        tx_t_stmt = tx_t_stmt.where(cast(Transaction.recorded_at, Date) <= date_to)
    for p, direction, amt in (await session.execute(tx_t_stmt)).all():
        if p:
            b = _ensure_bucket(p)
            if direction == TransactionDirection.DEBIT:
                b["collected_dec"] += Decimal(amt)
            elif direction == TransactionDirection.CREDIT:
                b["collected_dec"] -= Decimal(amt)

    # Projects by bucket
    p_t_stmt = (
        select(
            func.to_char(cast(Project.created_at, Date), time_fmt).label("p"),
            func.count(Project.id),
        )
        .where(Project.tenant_id == tenant_id)
        .group_by("p")
    )
    if client_id:
        p_t_stmt = p_t_stmt.where(Project.client_id == client_id)
    if project_id:
        p_t_stmt = p_t_stmt.where(Project.id == project_id)
    if date_from:
        p_t_stmt = p_t_stmt.where(cast(Project.created_at, Date) >= date_from)
    if date_to:
        p_t_stmt = p_t_stmt.where(cast(Project.created_at, Date) <= date_to)
    for p, cnt in (await session.execute(p_t_stmt)).all():
        if p:
            _ensure_bucket(p)["new_projects"] += int(cnt)

    # Clients by bucket
    c_t_stmt = (
        select(
            func.to_char(cast(Client.created_at, Date), time_fmt).label("p"),
            func.count(Client.id),
        )
        .where(Client.tenant_id == tenant_id)
        .group_by("p")
    )
    if client_id:
        c_t_stmt = c_t_stmt.where(Client.id == client_id)
    if date_from:
        c_t_stmt = c_t_stmt.where(cast(Client.created_at, Date) >= date_from)
    if date_to:
        c_t_stmt = c_t_stmt.where(cast(Client.created_at, Date) <= date_to)
    for p, cnt in (await session.execute(c_t_stmt)).all():
        if p:
            _ensure_bucket(p)["new_clients"] += int(cnt)

    # Services by bucket
    s_t_stmt = (
        select(
            func.to_char(cast(ProjectService.created_at, Date), time_fmt).label("p"),
            func.count(ProjectService.id),
        )
        .join(Project, ProjectService.project_id == Project.id)
        .where(Project.tenant_id == tenant_id)
        .group_by("p")
    )
    if client_id:
        s_t_stmt = s_t_stmt.where(Project.client_id == client_id)
    if project_id:
        s_t_stmt = s_t_stmt.where(Project.id == project_id)
    if date_from:
        s_t_stmt = s_t_stmt.where(cast(ProjectService.created_at, Date) >= date_from)
    if date_to:
        s_t_stmt = s_t_stmt.where(cast(ProjectService.created_at, Date) <= date_to)
    for p, cnt in (await session.execute(s_t_stmt)).all():
        if p:
            _ensure_bucket(p)["new_services"] += int(cnt)

    timeline: list[dict[str, Any]] = []
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

    # ── 8. Batch Project-wise Rollup ──────────────────────────────────────────
    p_filter = [Project.tenant_id == tenant_id]
    if client_id:
        p_filter.append(Project.client_id == client_id)
    if project_id:
        p_filter.append(Project.id == project_id)

    projects_raw = (
        await session.execute(
            select(Project)
            .where(*p_filter)
            .options(selectinload(Project.client))
            .order_by(Project.created_at.desc())
        )
    ).scalars().all()

    p_ids = [p.id for p in projects_raw]
    p_invoiced_map: dict[uuid.UUID, Decimal] = {}
    p_paid_map: dict[uuid.UUID, Decimal] = {}
    p_svc_count_map: dict[uuid.UUID, int] = {}
    p_svc_val_map: dict[uuid.UUID, Decimal] = {}

    if p_ids:
        # Invoiced per project
        p_inv_rows = (
            await session.execute(
                select(Invoice.project_id, func.coalesce(func.sum(Invoice.total), 0))
                .where(
                    Invoice.project_id.in_(p_ids),
                    Invoice.status.in_(_MONEY_STATUSES),
                )
                .group_by(Invoice.project_id)
            )
        ).all()
        for pid, amt in p_inv_rows:
            if pid:
                p_invoiced_map[pid] = Decimal(amt)

        # Allocations per project
        p_alloc_rows = (
            await session.execute(
                select(
                    Invoice.project_id,
                    func.coalesce(func.sum(PaymentAllocation.amount), 0),
                )
                .join(
                    InvoiceLineItem,
                    PaymentAllocation.line_item_id == InvoiceLineItem.id,
                )
                .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
                .where(
                    Invoice.project_id.in_(p_ids),
                    Invoice.status.in_(_MONEY_STATUSES),
                )
                .group_by(Invoice.project_id)
            )
        ).all()
        # Refunds per project
        p_ref_rows = (
            await session.execute(
                select(
                    Invoice.project_id,
                    func.coalesce(func.sum(Transaction.amount), 0),
                )
                .join(Invoice, Transaction.invoice_id == Invoice.id)
                .where(
                    Invoice.project_id.in_(p_ids),
                    Invoice.status.in_(_MONEY_STATUSES),
                    Transaction.direction == TransactionDirection.CREDIT,
                )
                .group_by(Invoice.project_id)
            )
        ).all()
        ref_dict = {pid: Decimal(amt) for pid, amt in p_ref_rows if pid}
        for pid, amt in p_alloc_rows:
            if pid:
                alloc = Decimal(amt)
                refund = ref_dict.get(pid, Decimal("0"))
                p_paid_map[pid] = _clamp(alloc - refund)

        # Service count and prices per project
        p_svc_rows = (
            await session.execute(
                select(
                    ProjectService.project_id,
                    func.count(ProjectService.id),
                    func.coalesce(func.sum(ProjectService.price_at_attachment), 0),
                )
                .where(ProjectService.project_id.in_(p_ids))
                .group_by(ProjectService.project_id)
            )
        ).all()
        for pid, cnt, val in p_svc_rows:
            if pid:
                p_svc_count_map[pid] = int(cnt)
                p_svc_val_map[pid] = Decimal(val)

    projects_list: list[dict[str, Any]] = []
    for p in projects_raw:
        inv = p_invoiced_map.get(p.id, Decimal("0"))
        paid = p_paid_map.get(p.id, Decimal("0"))
        due = _clamp(inv - paid)
        val = p_svc_val_map.get(p.id, Decimal("0"))
        # If project has a fixed or percent discount
        if p.discount_type and p.discount_value:
            if p.discount_type.value == "fixed":
                val = _clamp(val - Decimal(p.discount_value))
            elif p.discount_type.value == "percentage":
                disc = (val * Decimal(p.discount_value) / Decimal("100")).quantize(
                    Decimal("0.01")
                )
                val = _clamp(val - disc)

        projects_list.append(
            {
                "project_id": p.id,
                "short_id": str(p.id)[:6].upper(),
                "name": p.name,
                "client_id": p.client_id,
                "client_name": p.client.name if p.client else "",
                "status": p.status.value,
                "created_at": p.created_at,
                "services_count": p_svc_count_map.get(p.id, 0),
                "total_value": _fmt(val),
                "total_invoiced": _fmt(inv),
                "total_paid": _fmt(paid),
                "balance_due": _fmt(due),
            }
        )

    # ── 9. Batch Client-wise Rollup ───────────────────────────────────────────
    c_filter = [Client.tenant_id == tenant_id]
    if client_id:
        c_filter.append(Client.id == client_id)

    clients_raw = (
        await session.execute(
            select(Client).where(*c_filter).order_by(Client.name.asc())
        )
    ).scalars().all()
    c_ids = [c.id for c in clients_raw]

    c_active_proj_map: dict[uuid.UUID, int] = {}
    c_svc_count_map: dict[uuid.UUID, int] = {}
    c_invoiced_map: dict[uuid.UUID, Decimal] = {}
    c_paid_map: dict[uuid.UUID, Decimal] = {}
    c_adv_map: dict[uuid.UUID, Decimal] = {}

    if c_ids:
        # Active projects per client
        c_p_rows = (
            await session.execute(
                select(Project.client_id, func.count(Project.id))
                .where(
                    Project.client_id.in_(c_ids),
                    Project.tenant_id == tenant_id,
                )
                .group_by(Project.client_id)
            )
        ).all()
        for cid, cnt in c_p_rows:
            if cid:
                c_active_proj_map[cid] = int(cnt)

        # Services count per client
        c_s_rows = (
            await session.execute(
                select(Project.client_id, func.count(ProjectService.id))
                .join(ProjectService, ProjectService.project_id == Project.id)
                .where(
                    Project.client_id.in_(c_ids),
                    Project.tenant_id == tenant_id,
                )
                .group_by(Project.client_id)
            )
        ).all()
        for cid, cnt in c_s_rows:
            if cid:
                c_svc_count_map[cid] = int(cnt)

        # Invoiced per client
        c_inv_rows = (
            await session.execute(
                select(Project.client_id, func.coalesce(func.sum(Invoice.total), 0))
                .join(Invoice, Invoice.project_id == Project.id)
                .where(
                    Project.client_id.in_(c_ids),
                    Invoice.status.in_(_MONEY_STATUSES),
                )
                .group_by(Project.client_id)
            )
        ).all()
        for cid, amt in c_inv_rows:
            if cid:
                c_invoiced_map[cid] = Decimal(amt)

        # Allocations per client
        c_alloc_rows = (
            await session.execute(
                select(
                    Project.client_id,
                    func.coalesce(func.sum(PaymentAllocation.amount), 0),
                )
                .join(
                    InvoiceLineItem,
                    PaymentAllocation.line_item_id == InvoiceLineItem.id,
                )
                .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
                .join(Project, Invoice.project_id == Project.id)
                .where(
                    Project.client_id.in_(c_ids),
                    Invoice.status.in_(_MONEY_STATUSES),
                )
                .group_by(Project.client_id)
            )
        ).all()
        c_ref_rows = (
            await session.execute(
                select(
                    Project.client_id,
                    func.coalesce(func.sum(Transaction.amount), 0),
                )
                .join(Invoice, Transaction.invoice_id == Invoice.id)
                .join(Project, Invoice.project_id == Project.id)
                .where(
                    Project.client_id.in_(c_ids),
                    Invoice.status.in_(_MONEY_STATUSES),
                    Transaction.direction == TransactionDirection.CREDIT,
                )
                .group_by(Project.client_id)
            )
        ).all()
        c_ref_dict = {cid: Decimal(amt) for cid, amt in c_ref_rows if cid}
        for cid, amt in c_alloc_rows:
            if cid:
                alloc = Decimal(amt)
                refund = c_ref_dict.get(cid, Decimal("0"))
                c_paid_map[cid] = _clamp(alloc - refund)

        # Advance balance per client
        c_adv_rows = (
            await session.execute(
                select(
                    Advance.client_id,
                    func.coalesce(func.sum(Advance.remaining_amount), 0),
                )
                .where(
                    Advance.client_id.in_(c_ids),
                    Advance.tenant_id == tenant_id,
                    Advance.remaining_amount > Decimal("0"),
                )
                .group_by(Advance.client_id)
            )
        ).all()
        for cid, amt in c_adv_rows:
            if cid:
                c_adv_map[cid] = Decimal(amt)

    clients_list: list[dict[str, Any]] = []
    for c in clients_raw:
        inv = c_invoiced_map.get(c.id, Decimal("0"))
        paid = c_paid_map.get(c.id, Decimal("0"))
        due = _clamp(inv - paid)
        clients_list.append(
            {
                "client_id": c.id,
                "name": c.name,
                "client_type": c.client_type,
                "created_at": c.created_at,
                "active_projects_count": c_active_proj_map.get(c.id, 0),
                "total_services_count": c_svc_count_map.get(c.id, 0),
                "total_invoiced": _fmt(inv),
                "total_paid": _fmt(paid),
                "total_due": _fmt(due),
                "advance_balance": _fmt(c_adv_map.get(c.id, Decimal("0"))),
            }
        )

    return {
        "summary": summary,
        "timeline": timeline,
        "projects": projects_list,
        "clients": clients_list,
        "filters_applied": {
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "client_id": str(client_id) if client_id else None,
            "project_id": str(project_id) if project_id else None,
            "granularity": granularity,
        },
    }
