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
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.models.enums import InvoiceStatus
from app.models.invoice import Invoice
from app.models.tenant import Tenant
from app.storage import get_storage

_STATUS_LABELS: dict[InvoiceStatus, str] = {
    InvoiceStatus.DRAFT: "Draft",
    InvoiceStatus.ISSUED: "Issued",
    InvoiceStatus.PARTIALLY_PAID: "Partially Paid",
    InvoiceStatus.PAID: "Paid",
    InvoiceStatus.VOID: "Void",
}

_ITEM_COLUMNS = ["Description", "Qty", "Unit price", "Amount"]
_ITEM_COL_WIDTHS = [85 * mm, 25 * mm, 30 * mm, 30 * mm]

_LOGO_HEIGHT = 0.8 * inch
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _human_status(status: InvoiceStatus) -> str:
    return _STATUS_LABELS.get(status, status.value.replace("_", " ").title())


def _fmt(value: Any) -> str:
    """Format a Decimal/float as a fixed 2-decimal money string."""
    return f"{value:.2f}"


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
    """Render an invoice to a PDF byte string.

    `invoice` must have `line_items` and `project` eager-loaded. The
    project's client is fetched via the session because the invoice detail
    query does not eager-load it. Returns the PDF bytes; never writes.
    """
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

    # Branding (TODO-011/133): color for the title + rule, logo top-right.
    # The logo is read via the storage backend (branding.logo_key); absent
    # key/bytes silently skip the logo (legacy /uploads logos included).
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
    elements.append(Spacer(1, 8 * mm))

    # ── Line items table ──────────────────────────────────────────────────
    table_data: list[list[str]] = [_ITEM_COLUMNS]
    for item in sorted(invoice.line_items, key=lambda li: li.created_at):
        table_data.append(
            [
                item.description,
                _fmt(item.quantity),
                _fmt(item.unit_price),
                _fmt(item.amount),
            ]
        )
    items_table = Table(table_data, colWidths=_ITEM_COL_WIDTHS, repeatRows=1)
    items_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Totals ────────────────────────────────────────────────────────────
    totals = Table(
        [
            ["Subtotal", _fmt(invoice.subtotal)],
            ["Tax", _fmt(invoice.tax_total)],
            ["Total", _fmt(invoice.total)],
        ],
        colWidths=[85 * mm, 85 * mm],
    )
    totals.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.black),
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
