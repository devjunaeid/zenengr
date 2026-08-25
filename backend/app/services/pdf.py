"""Invoice PDF rendering (TODO-084/085).

Renders an invoice (with line items + project) into a monochrome PDF using
reportlab platypus. Pure read path: no session writes, no audit logging.

Usage:
    invoice = await invoice_service.get_invoice(...)  # line_items + project
    tenant = await session.get(Tenant, tenant_id)
    pdf = await render_invoice_pdf(session, invoice=invoice, tenant=tenant)
"""

from __future__ import annotations

import re
from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.enums import InvoiceStatus, TransactionDirection
from app.models.invoice import Invoice
from app.models.tenant import Tenant
from app.models.transaction import Transaction
from app.services.settings import get_tenant_setting_by_key
from app.storage import get_storage

_STATUS_LABELS: dict[InvoiceStatus, str] = {
    InvoiceStatus.DRAFT: "Draft",
    InvoiceStatus.ISSUED: "Issued",
    InvoiceStatus.PARTIALLY_PAID: "Partially Paid",
    InvoiceStatus.PAID: "Paid",
    InvoiceStatus.VOID: "Void",
}

_ITEM_COLUMNS = ["Date", "Description", "Qty", "Unit price", "Amount"]
_ITEM_COL_WIDTHS = [25 * mm, 60 * mm, 20 * mm, 32 * mm, 33 * mm]

_LOGO_HEIGHT = 0.8 * inch
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _human_status(status: InvoiceStatus) -> str:
    return _STATUS_LABELS.get(status, status.value.replace("_", " ").title())


def _fmt(value: Any) -> str:
    """Format a Decimal/float as a fixed 2-decimal money string."""
    return f"{value:.2f}"


def _money(value: Any, code: str) -> str:
    """Format a money value with the tenant's currency code prefix.

    Uses the ISO code (e.g. "BDT 500.00"), never a symbol: non-Latin
    currency glyphs break the built-in WinAnsi Helvetica fonts.
    """
    return f"{code} {value:.2f}"


def _parse_hex_color(value: Any) -> colors.Color | None:
    """Parse a #RRGGBB hex string into a reportlab color. None if invalid."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not _HEX_COLOR_RE.match(stripped):
        return None
    return colors.HexColor(stripped)


def _draw_logo(canv: Any, doc: Any, logo_bytes: bytes) -> None:
    """Draw the tenant logo top-right of the page. Any error skips the logo."""
    try:
        reader = ImageReader(BytesIO(logo_bytes))
        iw, ih = reader.getSize()
        if iw <= 0 or ih <= 0:
            return
        target_w = _LOGO_HEIGHT * iw / ih
        x = doc.pagesize[0] - doc.rightMargin - target_w
        y = doc.pagesize[1] - doc.topMargin - _LOGO_HEIGHT
        canv.drawImage(
            BytesIO(logo_bytes),
            x,
            y,
            width=target_w,
            height=_LOGO_HEIGHT,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        return


async def render_invoice_pdf(
    session: AsyncSession,
    *,
    invoice: Invoice,
    tenant: Tenant | None,
) -> bytes:
    """Render an invoice to a PDF byte string with line items, transactions, and balance due."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("InvoiceTitle", parent=styles["Title"], alignment=1, fontSize=18)
    footer_style = ParagraphStyle(
        "InvoiceFooter", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )

    branding: dict[str, Any] = tenant.branding if tenant is not None else {}
    brand_color = _parse_hex_color(branding.get("color"))
    logo_key = branding.get("logo_key")
    logo_bytes: bytes | None = None
    if isinstance(logo_key, str) and logo_key:
        logo_bytes = await get_storage().get(logo_key)
    if brand_color is not None:
        title_style = ParagraphStyle(
            "InvoiceTitle",
            parent=title_style,
            textColor=brand_color,
        )

    currency_code = "USD"
    if tenant is not None:
        currency_setting = await get_tenant_setting_by_key(session, tenant.id, "currency")
        if currency_setting is not None and currency_setting.value:
            currency_code = currency_setting.value
    currency_code = currency_code.upper()

    # Query all payments / transactions recorded against this invoice
    tx_stmt = (
        select(Transaction)
        .where(Transaction.invoice_id == invoice.id)
        .order_by(Transaction.recorded_at, Transaction.created_at)
    )
    transactions = list((await session.execute(tx_stmt)).scalars().all())

    payments = sum(
        (tx.amount for tx in transactions if tx.direction == TransactionDirection.DEBIT),
        Decimal("0"),
    )
    refunds = sum(
        (tx.amount for tx in transactions if tx.direction == TransactionDirection.CREDIT),
        Decimal("0"),
    )
    total_paid = Decimal(f"{payments - refunds:.2f}")
    inv_total = Decimal(f"{invoice.total:.2f}")
    balance_due = Decimal(f"{max(inv_total - total_paid, Decimal('0')):.2f}")
    advance_credit = Decimal(f"{max(total_paid - inv_total, Decimal('0')):.2f}")

    elements: list[Any] = []
    elements.append(Paragraph("INVOICE", title_style))
    if brand_color is not None:
        elements.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=brand_color,
                spaceBefore=2 * mm,
                spaceAfter=4 * mm,
            )
        )
    else:
        elements.append(Spacer(1, 6 * mm))

    # ── Header: business name, number, status, project/client, dates ──────
    elements.append(
        Paragraph(f"<b>{tenant.business_name if tenant else 'Invoice'}</b>", styles["Heading2"])
    )
    elements.append(Paragraph(f"Number: {invoice.invoice_number or 'DRAFT'}", styles["Normal"]))
    elements.append(Paragraph(f"Status: {_human_status(invoice.status)}", styles["Normal"]))
    if invoice.project is not None:
        elements.append(Paragraph(f"Project: {invoice.project.name}", styles["Normal"]))
        client: Client | None = None
        if invoice.project.client_id is not None:
            client = await session.get(Client, invoice.project.client_id)
        if client is not None:
            elements.append(Paragraph(f"Client: {client.name}", styles["Normal"]))
    if invoice.issue_date is not None:
        elements.append(
            Paragraph(f"Issue date: {invoice.issue_date.isoformat()}", styles["Normal"])
        )
    if invoice.due_date is not None:
        elements.append(Paragraph(f"Due date: {invoice.due_date.isoformat()}", styles["Normal"]))
    elements.append(Spacer(1, 6 * mm))

    # ── Line items table ──────────────────────────────────────────────────
    table_data: list[list[str]] = [_ITEM_COLUMNS]
    for item in sorted(invoice.line_items, key=lambda li: li.created_at):
        table_data.append(
            [
                item.entry_date.isoformat() if item.entry_date is not None else "—",
                item.description,
                _fmt(item.quantity),
                _money(item.unit_price, currency_code),
                _money(item.amount, currency_code),
            ]
        )
    items_table = Table(table_data, colWidths=_ITEM_COL_WIDTHS, repeatRows=1)
    items_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Totals summary with inline payment entries ────────────────────────
    totals_data: list[list[str]] = [
        ["Subtotal", _money(invoice.subtotal, currency_code)],
    ]
    if Decimal(str(invoice.tax_total)) > 0:
        totals_data.append(["Tax", _money(invoice.tax_total, currency_code)])

    total_row_idx = len(totals_data)
    totals_data.append(["Total", _money(invoice.total, currency_code)])

    for tx in transactions:
        t_type = "Refund" if tx.direction == TransactionDirection.CREDIT else "Payment"
        t_date = tx.recorded_at.date().isoformat() if tx.recorded_at else "—"
        t_method = tx.method.value.replace("_", " ").title()
        ref_text = f" ({tx.reference_note})" if tx.reference_note else ""
        label = f"{t_date} - {t_type} - {t_method}{ref_text}"
        amt_str = f"-{_money(tx.amount, currency_code)}" if tx.direction == TransactionDirection.DEBIT else f"+{_money(tx.amount, currency_code)}"
        totals_data.append([label, amt_str])

    due_row_idx = len(totals_data)
    totals_data.append(["Due", _money(balance_due, currency_code)])
    if advance_credit > 0:
        totals_data.append(["Advance Credit", _money(advance_credit, currency_code)])

    totals = Table(totals_data, colWidths=[105 * mm, 65 * mm])
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, total_row_idx), (-1, total_row_idx), "Helvetica-Bold"),
                ("LINEABOVE", (0, total_row_idx), (-1, total_row_idx), 0.5, colors.black),
                ("FONTNAME", (0, due_row_idx), (-1, due_row_idx), "Helvetica-Bold"),
                ("LINEABOVE", (0, due_row_idx), (-1, due_row_idx), 0.5, colors.black),
            ]
        )
    )
    elements.append(totals)

    # ── Notes ─────────────────────────────────────────────────────────────
    if invoice.notes:
        elements.append(Spacer(1, 6 * mm))
        elements.append(Paragraph(f"Notes: {invoice.notes}", styles["Normal"]))

    # ── Footer ────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 12 * mm))
    elements.append(Paragraph("Generated by ZenEngr", footer_style))

    if logo_bytes:
        doc.build(
            elements,
            onFirstPage=lambda canv, doc: _draw_logo(canv, doc, logo_bytes),
        )
    else:
        doc.build(elements)
    return buf.getvalue()


async def render_project_statement_pdf(
    session: AsyncSession,
    *,
    project_id: Any,
    tenant: Tenant | None,
) -> bytes:
    """Render a live statement of account PDF for a project.

    Combines all project charges (services) and payments/advances in chronological
    order, along with live Subtotal, Total, Paid, Balance Due, and Advance Balance.
    """
    from datetime import date
    from app.models.project import Project
    from app.models.client import Client
    from app.models.enums import LedgerEntryType
    from app.services.ledger import get_project_ledger

    if tenant is None:
        return b""

    stmt = select(Project).where(Project.id == project_id, Project.tenant_id == tenant.id)
    project = (await session.execute(stmt)).scalar_one_or_none()
    if project is None:
        return b""

    client: Client | None = None
    if project.client_id is not None:
        client = await session.get(Client, project.client_id)

    ledger = await get_project_ledger(session, tenant_id=tenant.id, project_id=project.id)
    entries = ledger["entries"]
    summary = ledger["summary"]

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("StatementTitle", parent=styles["Title"], alignment=1, fontSize=18)
    footer_style = ParagraphStyle(
        "StatementFooter", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )

    branding: dict[str, Any] = tenant.branding if tenant is not None else {}
    brand_color = _parse_hex_color(branding.get("color"))
    logo_key = branding.get("logo_key")
    logo_bytes: bytes | None = None
    if isinstance(logo_key, str) and logo_key:
        logo_bytes = await get_storage().get(logo_key)
    if brand_color is not None:
        title_style = ParagraphStyle(
            "StatementTitle",
            parent=title_style,
            textColor=brand_color,
        )

    currency_code = "USD"
    if tenant is not None:
        currency_setting = await get_tenant_setting_by_key(session, tenant.id, "currency")
        if currency_setting is not None and currency_setting.value:
            currency_code = currency_setting.value
    currency_code = currency_code.upper()

    elements: list[Any] = []
    elements.append(Paragraph("PROJECT FINANCIAL STATEMENT", title_style))
    if brand_color is not None:
        elements.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=brand_color,
                spaceBefore=2 * mm,
                spaceAfter=4 * mm,
            )
        )
    else:
        elements.append(Spacer(1, 6 * mm))

    # ── Header info ───────────────────────────────────────────────────────
    elements.append(
        Paragraph(f"<b>{tenant.business_name if tenant else 'Statement'}</b>", styles["Heading2"])
    )
    elements.append(Paragraph(f"Project: {project.name}", styles["Normal"]))
    if client is not None:
        elements.append(Paragraph(f"Client: {client.name}", styles["Normal"]))
    elements.append(Paragraph(f"Statement Date: {date.today().isoformat()}", styles["Normal"]))
    elements.append(Paragraph("Status: Live Project Financial Summary", styles["Normal"]))
    elements.append(Spacer(1, 6 * mm))

    # ── Chronological Entries Table ───────────────────────────────────────
    table_data: list[list[str]] = [["Date", "Type", "Description / Ref", "Invoice #", "Amount"]]
    for e in entries:
        is_charge = e["type"] == LedgerEntryType.CHARGE or e["type"] == "charge"
        type_label = "Charge" if is_charge else ("Refund" if (e["type"] == LedgerEntryType.REFUND or e["type"] == "refund") else "Payment")
        amount_val = Decimal(e["amount"])
        inv_num = e.get("invoice_number") or (f"INV Ref" if e.get("invoice_ref") else "—")
        table_data.append(
            [
                e["entry_date"].isoformat() if hasattr(e["entry_date"], "isoformat") else str(e["entry_date"]),
                type_label,
                e["description"],
                inv_num,
                _money(amount_val, currency_code),
            ]
        )

    col_widths = [25 * mm, 20 * mm, 75 * mm, 25 * mm, 25 * mm]
    entries_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    entries_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (4, 0), (4, -1), "RIGHT"),
            ]
        )
    )
    elements.append(entries_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Summary Totals ────────────────────────────────────────────────────
    subtotal_dec = Decimal(summary["subtotal"])
    discount_dec = Decimal(summary["discount_amount"])
    total_dec = Decimal(summary["total"])
    paid_dec = Decimal(summary["paid"])
    due_dec = Decimal(summary["due"])
    advance_dec = Decimal(summary.get("advance_balance", "0.00"))

    summary_rows = [
        ["Total Charges (Subtotal)", _money(subtotal_dec, currency_code)],
    ]
    if discount_dec > 0:
        summary_rows.append(["Project Discount", f"-{_money(discount_dec, currency_code)}"])
        summary_rows.append(["Net Total", _money(total_dec, currency_code)])
    summary_rows.append(["Total Paid / Credits", _money(paid_dec, currency_code)])
    summary_rows.append(["Net Balance Due", _money(due_dec, currency_code)])
    if advance_dec > 0:
        summary_rows.append(["Advance Credit (Overpayment)", _money(advance_dec, currency_code)])

    totals_table = Table(summary_rows, colWidths=[85 * mm, 85 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -2), (-1, -2), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -2), (-1, -2), 0.5, colors.black),
            ]
        )
    )
    elements.append(totals_table)

    # ── Footer ────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 12 * mm))
    elements.append(Paragraph("Generated by ZenEngr", footer_style))

    if logo_bytes:
        doc.build(
            elements,
            onFirstPage=lambda canv, doc: _draw_logo(canv, doc, logo_bytes),
        )
    else:
        doc.build(elements)
    return buf.getvalue()

