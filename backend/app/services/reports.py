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

from sqlalchemy import Date, case, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

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
    tab: str = "all",
) -> dict[str, Any]:
    """Compile organization-wide financial and operational reporting.

    Uses high-performance batch SQL aggregates with zero N+1 queries.
    """
    inv_date_col = func.coalesce(Invoice.issue_date, cast(Invoice.created_at, Date))

    # ── 1. Combined Executive Summary Query ──────────────────────────────────
    # New projects count
    proj_q = select(func.count(Project.id)).where(Project.tenant_id == tenant_id)
    if client_id:
        proj_q = proj_q.where(Project.client_id == client_id)
    if project_id:
        proj_q = proj_q.where(Project.id == project_id)
    if date_from:
        proj_q = proj_q.where(cast(Project.created_at, Date) >= date_from)
    if date_to:
        proj_q = proj_q.where(cast(Project.created_at, Date) <= date_to)

    # New clients count
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

    # New services count & value
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

    # Invoiced in range
    inv_range_q = select(func.coalesce(func.sum(Invoice.total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.status.in_(_MONEY_STATUSES),
    )
    if project_id:
        inv_range_q = inv_range_q.where(Invoice.project_id == project_id)
    elif client_id:
        inv_range_q = inv_range_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        inv_range_q = inv_range_q.where(inv_date_col >= date_from)
    if date_to:
        inv_range_q = inv_range_q.where(inv_date_col <= date_to)

    # Collections in range
    tx_range_q = (
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
        )
    )
    if project_id:
        tx_range_q = tx_range_q.where(Invoice.project_id == project_id)
    elif client_id:
        tx_range_q = tx_range_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )
    if date_from:
        tx_range_q = tx_range_q.where(cast(Transaction.recorded_at, Date) >= date_from)
    if date_to:
        tx_range_q = tx_range_q.where(cast(Transaction.recorded_at, Date) <= date_to)

    # Lifetime invoiced
    life_inv_q = select(func.coalesce(func.sum(Invoice.total), 0)).where(
        Invoice.tenant_id == tenant_id,
        Invoice.status.in_(_MONEY_STATUSES),
    )
    if project_id:
        life_inv_q = life_inv_q.where(Invoice.project_id == project_id)
    elif client_id:
        life_inv_q = life_inv_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )

    # Lifetime payments
    life_alloc_q = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
        )
    )
    if project_id:
        life_alloc_q = life_alloc_q.where(Invoice.project_id == project_id)
    elif client_id:
        life_alloc_q = life_alloc_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )

    life_ref_q = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Invoice, Transaction.invoice_id == Invoice.id)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(_MONEY_STATUSES),
            Transaction.direction == TransactionDirection.CREDIT,
        )
    )
    if project_id:
        life_ref_q = life_ref_q.where(Invoice.project_id == project_id)
    elif client_id:
        life_ref_q = life_ref_q.join(Project, Invoice.project_id == Project.id).where(
            Project.client_id == client_id
        )

    # Advances
    adv_q = select(func.coalesce(func.sum(Advance.remaining_amount), 0)).where(
        Advance.tenant_id == tenant_id,
        Advance.remaining_amount > Decimal("0"),
    )
    if client_id:
        adv_q = adv_q.where(Advance.client_id == client_id)
    elif project_id:
        # Advance belongs to client; if project is selected, show that client's advance
        p_cli_sub = select(Project.client_id).where(Project.id == project_id).scalar_subquery()
        adv_q = adv_q.where(Advance.client_id == p_cli_sub)

    # Consolidate into single query
    summary_stmt = select(
        proj_q.scalar_subquery().label("new_projects"),
        cli_q.scalar_subquery().label("new_clients"),
        select(svc_q.subquery().c.cnt).scalar_subquery().label("new_services"),
        select(svc_q.subquery().c.val).scalar_subquery().label("new_services_val"),
        inv_range_q.scalar_subquery().label("invoiced_range"),
        tx_range_q.scalar_subquery().label("collected_range"),
        life_inv_q.scalar_subquery().label("life_inv"),
        life_alloc_q.scalar_subquery().label("life_alloc"),
        life_ref_q.scalar_subquery().label("life_ref"),
        adv_q.scalar_subquery().label("advances"),
    )
    s_row = (await session.execute(summary_stmt)).one()

    new_projects_count = int(s_row.new_projects or 0)
    new_clients_count = int(s_row.new_clients or 0)
    new_services_count = int(s_row.new_services or 0)
    new_services_value = Decimal(s_row.new_services_val or 0)
    total_invoiced_in_range = Decimal(s_row.invoiced_range or 0)
    net_collected_in_range = _clamp(Decimal(s_row.collected_range or 0))
    lifetime_invoiced = Decimal(s_row.life_inv or 0)
    lifetime_paid = _clamp(Decimal(s_row.life_alloc or 0) - Decimal(s_row.life_ref or 0))
    total_due = _clamp(lifetime_invoiced - lifetime_paid)
    total_advance_balance = Decimal(s_row.advances or 0)

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

    # ── 2. Unified Timeline Series (Single Query Union) ──────────────────────
    timeline: list[dict[str, Any]] = []
    if tab in ("all", "timeline"):
        time_fmt = "YYYY-MM" if granularity == "month" else "YYYY-MM-DD"

        # 1. Invoices
        q1 = (
            select(
                func.to_char(inv_date_col, time_fmt).label("p"),
                literal("inv").label("kind"),
                func.coalesce(func.sum(Invoice.total), 0).label("num1"),
                literal(0).label("num2"),
            )
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(_MONEY_STATUSES),
            )
        )
        if project_id:
            q1 = q1.where(Invoice.project_id == project_id)
        elif client_id:
            q1 = q1.join(Project, Invoice.project_id == Project.id).where(
                Project.client_id == client_id
            )
        if date_from:
            q1 = q1.where(inv_date_col >= date_from)
        if date_to:
            q1 = q1.where(inv_date_col <= date_to)
        q1 = q1.group_by("p")

        # 2. Transactions
        q2 = (
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
            )
        )
        if project_id:
            q2 = q2.where(Invoice.project_id == project_id)
        elif client_id:
            q2 = q2.join(Project, Invoice.project_id == Project.id).where(
                Project.client_id == client_id
            )
        if date_from:
            q2 = q2.where(cast(Transaction.recorded_at, Date) >= date_from)
        if date_to:
            q2 = q2.where(cast(Transaction.recorded_at, Date) <= date_to)
        q2 = q2.group_by("p", "num2")

        # 3. Projects
        q3 = (
            select(
                func.to_char(cast(Project.created_at, Date), time_fmt).label("p"),
                literal("proj").label("kind"),
                func.count(Project.id).label("num1"),
                literal(0).label("num2"),
            )
            .where(Project.tenant_id == tenant_id)
        )
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
            q4 = (
                select(
                    func.to_char(cast(Client.created_at, Date), time_fmt).label("p"),
                    literal("client").label("kind"),
                    func.count(Client.id).label("num1"),
                    literal(0).label("num2"),
                )
                .where(Client.tenant_id == tenant_id)
            )
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

        all_queries = [q1, q2, q3, q5]
        if q4 is not None:
            all_queries.append(q4)

        u = union_all(*all_queries).subquery()
        timeline_rows = (
            await session.execute(select(u.c.p, u.c.kind, u.c.num1, u.c.num2))
        ).all()

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
            if kind == "inv":
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

    # ── 3. Unified Project Rollup (Single CTE Query) ─────────────────────────
    projects_list: list[dict[str, Any]] = []
    if tab in ("all", "projects"):
        p_filter = [Project.tenant_id == tenant_id]
        if client_id:
            p_filter.append(Project.client_id == client_id)
        if project_id:
            p_filter.append(Project.id == project_id)

        inv_sub = (
            select(
                Invoice.project_id,
                func.coalesce(func.sum(Invoice.total), 0).label("invoiced"),
            )
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(_MONEY_STATUSES),
            )
            .group_by(Invoice.project_id)
            .cte("p_inv_sub")
        )

        alloc_sub = (
            select(
                Invoice.project_id,
                func.coalesce(func.sum(PaymentAllocation.amount), 0).label("allocated"),
            )
            .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(_MONEY_STATUSES),
            )
            .group_by(Invoice.project_id)
            .cte("p_alloc_sub")
        )

        ref_sub = (
            select(
                Invoice.project_id,
                func.coalesce(func.sum(Transaction.amount), 0).label("refunded"),
            )
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(_MONEY_STATUSES),
                Transaction.direction == TransactionDirection.CREDIT,
            )
            .group_by(Invoice.project_id)
            .cte("p_ref_sub")
        )

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
                func.coalesce(inv_sub.c.invoiced, 0).label("total_invoiced"),
                func.coalesce(alloc_sub.c.allocated, 0).label("total_alloc"),
                func.coalesce(ref_sub.c.refunded, 0).label("total_ref"),
                func.coalesce(svc_sub.c.svc_cnt, 0).label("services_count"),
                func.coalesce(svc_sub.c.svc_val, 0).label("services_value"),
            )
            .outerjoin(Client, Project.client_id == Client.id)
            .outerjoin(inv_sub, Project.id == inv_sub.c.project_id)
            .outerjoin(alloc_sub, Project.id == alloc_sub.c.project_id)
            .outerjoin(ref_sub, Project.id == ref_sub.c.project_id)
            .outerjoin(svc_sub, Project.id == svc_sub.c.project_id)
            .where(*p_filter)
            .order_by(Project.created_at.desc())
        )

        proj_rows = (await session.execute(p_stmt)).all()
        for p in proj_rows:
            inv = Decimal(p.total_invoiced)
            paid = _clamp(Decimal(p.total_alloc) - Decimal(p.total_ref))
            val = Decimal(p.services_value)
            if p.discount_type and p.discount_value:
                if p.discount_type.value == "fixed":
                    val = _clamp(val - Decimal(p.discount_value))
                elif p.discount_type.value == "percentage":
                    disc = (val * Decimal(p.discount_value) / Decimal("100")).quantize(
                        Decimal("0.01")
                    )
                    val = _clamp(val - disc)
            billed = val if val > 0 else inv
            due = _clamp(billed - paid)

            projects_list.append(
                {
                    "project_id": p.id,
                    "short_id": str(p.id)[:6].upper(),
                    "name": p.name,
                    "client_id": p.client_id,
                    "client_name": p.client_name,
                    "status": p.status.value,
                    "created_at": p.created_at,
                    "services_count": int(p.services_count),
                    "total_value": _fmt(billed),
                    "total_invoiced": _fmt(billed),
                    "total_paid": _fmt(paid),
                    "balance_due": _fmt(due),
                }
            )

    # ── 4. Unified Client Rollup (Single CTE Query) ──────────────────────────
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

        cp_sub = (
            select(Project.client_id, func.count(Project.id).label("active_projects"))
            .where(Project.tenant_id == tenant_id)
            .group_by(Project.client_id)
            .cte("cp_sub")
        )
        cs_sub = (
            select(
                Project.client_id,
                func.count(ProjectService.id).label("services_count"),
                func.coalesce(
                    func.sum(ProjectService.price_at_attachment), 0
                ).label("services_val"),
            )
            .join(ProjectService, ProjectService.project_id == Project.id)
            .where(Project.tenant_id == tenant_id)
            .group_by(Project.client_id)
            .cte("cs_sub")
        )
        cinv_sub = (
            select(Project.client_id, func.coalesce(func.sum(Invoice.total), 0).label("invoiced"))
            .join(Invoice, Invoice.project_id == Project.id)
            .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(_MONEY_STATUSES))
            .group_by(Project.client_id)
            .cte("cinv_sub")
        )
        calloc_sub = (
            select(
                Project.client_id,
                func.coalesce(func.sum(PaymentAllocation.amount), 0).label("allocated"),
            )
            .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
            .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
            .join(Project, Invoice.project_id == Project.id)
            .where(Invoice.tenant_id == tenant_id, Invoice.status.in_(_MONEY_STATUSES))
            .group_by(Project.client_id)
            .cte("calloc_sub")
        )
        cref_sub = (
            select(
                Project.client_id,
                func.coalesce(func.sum(Transaction.amount), 0).label("refunded"),
            )
            .join(Invoice, Transaction.invoice_id == Invoice.id)
            .join(Project, Invoice.project_id == Project.id)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status.in_(_MONEY_STATUSES),
                Transaction.direction == TransactionDirection.CREDIT,
            )
            .group_by(Project.client_id)
            .cte("cref_sub")
        )
        cadv_sub = (
            select(
                Advance.client_id,
                func.coalesce(func.sum(Advance.remaining_amount), 0).label("advances"),
            )
            .where(Advance.tenant_id == tenant_id, Advance.remaining_amount > Decimal("0"))
            .group_by(Advance.client_id)
            .cte("cadv_sub")
        )

        c_stmt = (
            select(
                Client.id,
                Client.name,
                Client.client_type,
                Client.created_at,
                func.coalesce(cp_sub.c.active_projects, 0).label("active_projects_count"),
                func.coalesce(cs_sub.c.services_count, 0).label("total_services_count"),
                func.coalesce(cs_sub.c.services_val, 0).label("services_val"),
                func.coalesce(cinv_sub.c.invoiced, 0).label("total_invoiced"),
                func.coalesce(calloc_sub.c.allocated, 0).label("total_allocated"),
                func.coalesce(cref_sub.c.refunded, 0).label("total_refunded"),
                func.coalesce(cadv_sub.c.advances, 0).label("advance_balance"),
            )
            .outerjoin(cp_sub, Client.id == cp_sub.c.client_id)
            .outerjoin(cs_sub, Client.id == cs_sub.c.client_id)
            .outerjoin(cinv_sub, Client.id == cinv_sub.c.client_id)
            .outerjoin(calloc_sub, Client.id == calloc_sub.c.client_id)
            .outerjoin(cref_sub, Client.id == cref_sub.c.client_id)
            .outerjoin(cadv_sub, Client.id == cadv_sub.c.client_id)
            .where(*c_filter)
            .order_by(Client.name.asc())
        )

        client_rows = (await session.execute(c_stmt)).all()
        for c in client_rows:
            s_val = Decimal(c.services_val)
            inv = Decimal(c.total_invoiced)
            billed = s_val if s_val > 0 else inv
            paid = _clamp(Decimal(c.total_allocated) - Decimal(c.total_refunded))
            due = _clamp(billed - paid)
            clients_list.append(
                {
                    "client_id": c.id,
                    "name": c.name,
                    "client_type": c.client_type,
                    "created_at": c.created_at,
                    "active_projects_count": int(c.active_projects_count),
                    "total_services_count": int(c.total_services_count),
                    "total_invoiced": _fmt(billed),
                    "total_paid": _fmt(paid),
                    "total_due": _fmt(due),
                    "advance_balance": _fmt(c.advance_balance),
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
            "tab": tab,
        },
    }
