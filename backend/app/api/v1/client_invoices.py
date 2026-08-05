"""Client-scoped invoice endpoints (client portal data, TODO-081).

Base path: /api/v1/client/invoices
Client users see only invoices on their own client's projects. Void invoices
are filtered OUT of the client list (the tenant list keeps them), so a client
cannot see cancelled numbers in their portal.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_client_user
from app.db.session import get_session
from app.models.client_user import ClientUser
from app.models.enums import InvoiceStatus, TransactionDirection
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.project import Project
from app.models.tenant import Tenant
from app.models.transaction import PaymentAllocation, Transaction
from app.schemas.client_portal import (
    ClientInvoiceDetailResponse,
    ClientInvoiceListItem,
    ClientInvoiceListResponse,
)
from app.schemas.invoices import InvoiceLineItemResponse
from app.schemas.transactions import PaymentAllocationResponse, TransactionResponse
from app.services import pdf as pdf_service

router = APIRouter(prefix="/client/invoices", tags=["client-invoices"])


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


def _parse_status(value: str) -> InvoiceStatus:
    try:
        return InvoiceStatus(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Invalid status: {value}. "
                "Must be 'draft', 'issued', 'partially_paid', 'paid', or 'void'."
            ),
        ) from None


def _to_line_item_response(item: Any) -> InvoiceLineItemResponse:
    return InvoiceLineItemResponse(
        id=item.id,
        description=item.description,
        quantity=f"{item.quantity:.2f}",
        unit_price=f"{item.unit_price:.2f}",
        amount=f"{item.amount:.2f}",
        service_id=item.service_id,
        project_service_id=item.project_service_id,
    )


def _clamp_non_negative(value: Decimal) -> Decimal:
    return value if value >= Decimal("0") else Decimal("0")


def _to_transaction_response(tx: Any) -> TransactionResponse:
    """Mirror of the tenant-side builder in api/v1/invoices.py (client portal)."""
    allocations = sorted(tx.allocations, key=lambda a: a.created_at)
    return TransactionResponse(
        id=tx.id,
        invoice_id=tx.invoice_id,
        amount=f"{tx.amount:.2f}",
        direction=tx.direction,
        method=tx.method,
        reference_note=tx.reference_note,
        recorded_by_id=tx.recorded_by_id,
        recorded_at=tx.recorded_at,
        allocations=[
            PaymentAllocationResponse(
                id=a.id,
                line_item_id=a.line_item_id,
                amount=f"{a.amount:.2f}",
            )
            for a in allocations
        ],
    )


def _client_invoice_scope(user: ClientUser) -> tuple[Any, Any]:
    """Base WHERE clause: invoice belongs to the caller's client + tenant."""
    return (
        Invoice.tenant_id == user.tenant_id,
        Project.client_id == user.client_id,
    )


@router.get("/", response_model=ClientInvoiceListResponse)
async def list_client_invoices_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_val: str | None = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> ClientInvoiceListResponse:
    """List the client's invoices (void invoices excluded)."""
    status_filter: InvoiceStatus | None = None
    if status_val:
        status_filter = _parse_status(status_val)

    base = (
        select(Invoice)
        .options(selectinload(Invoice.project))
        .join(Project, Invoice.project_id == Project.id)
        .where(*_client_invoice_scope(user))
        # Void invoices stay on the tenant ledger but are hidden from the portal.
        .where(Invoice.status != InvoiceStatus.VOID)
    )
    if status_filter is not None:
        base = base.where(Invoice.status == status_filter)

    total: int = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    result = await session.execute(
        base.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    invoices = list(result.unique().scalars().all())

    items = [
        ClientInvoiceListItem(
            id=inv.id,
            invoice_number=inv.invoice_number,
            status=inv.status,
            project_id=inv.project_id,
            project_name=inv.project.name if inv.project else "",
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            total=f"{inv.total:.2f}",
            created_at=inv.created_at,
        )
        for inv in invoices
    ]
    return ClientInvoiceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{invoice_id}", response_model=ClientInvoiceDetailResponse)
async def get_client_invoice_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> ClientInvoiceDetailResponse:
    """Invoice detail with line items + paid/balance amounts (client-scoped).

    404 for invoices that do not belong to the caller's client (leak prevention).
    """
    iid = _parse_uuid(invoice_id, kind="Invoice")
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.project))
        .join(Project, Invoice.project_id == Project.id)
        .where(Invoice.id == iid, *_client_invoice_scope(user))
    )
    result = await session.execute(stmt)
    invoice = result.unique().scalar_one_or_none()
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    paid_q = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(InvoiceLineItem, PaymentAllocation.line_item_id == InvoiceLineItem.id)
        .where(InvoiceLineItem.invoice_id == invoice.id)
    )
    paid_allocations = Decimal((await session.execute(paid_q)).scalar_one())
    refund_q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
        Transaction.invoice_id == invoice.id,
        Transaction.direction == TransactionDirection.CREDIT,
    )
    refunds = Decimal((await session.execute(refund_q)).scalar_one())
    paid = _clamp_non_negative(paid_allocations - refunds)
    paid_amount = f"{paid:.2f}"
    balance_due = f"{_clamp_non_negative(Decimal(invoice.total) - paid):.2f}"

    line_items = sorted(invoice.line_items, key=lambda li: li.created_at)
    return ClientInvoiceDetailResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        project_id=invoice.project_id,
        project_name=invoice.project.name if invoice.project else "",
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        subtotal=f"{invoice.subtotal:.2f}",
        tax_total=f"{invoice.tax_total:.2f}",
        total=f"{invoice.total:.2f}",
        notes=invoice.notes,
        paid_amount=paid_amount,
        balance_due=balance_due,
        line_items=[_to_line_item_response(li) for li in line_items],
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


@router.get("/{invoice_id}/transactions", response_model=list[TransactionResponse])
async def get_client_invoice_transactions_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> list[TransactionResponse]:
    """List payments recorded against one of the client's invoices (TODO-098).

    Client-scoped: invoices that do not belong to the caller's client return
    404 (leak prevention). Void invoices keep their payment history visible.
    """
    iid = _parse_uuid(invoice_id, kind="Invoice")
    inv_stmt = (
        select(Invoice)
        .join(Project, Invoice.project_id == Project.id)
        .where(Invoice.id == iid, *_client_invoice_scope(user))
    )
    invoice = (await session.execute(inv_stmt)).unique().scalar_one_or_none()
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    tx_stmt = (
        select(Transaction)
        .options(selectinload(Transaction.allocations))
        .where(Transaction.invoice_id == invoice.id)
        .order_by(Transaction.recorded_at.asc())
    )
    txs = list((await session.execute(tx_stmt)).unique().scalars().all())
    return [_to_transaction_response(tx) for tx in txs]


@router.get("/{invoice_id}/pdf")
async def get_client_invoice_pdf_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: ClientUser = Depends(get_current_client_user),
) -> Response:
    """Render one of the client's invoices as a PDF attachment (TODO-084/085).

    Client-scoped: invoices that do not belong to the caller's client return
    404 (leak prevention), mirroring the detail endpoint.
    """
    iid = _parse_uuid(invoice_id, kind="Invoice")
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.line_items), selectinload(Invoice.project))
        .join(Project, Invoice.project_id == Project.id)
        .where(Invoice.id == iid, *_client_invoice_scope(user))
    )
    result = await session.execute(stmt)
    invoice = result.unique().scalar_one_or_none()
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )

    tenant = await session.get(Tenant, user.tenant_id)
    pdf_bytes = await pdf_service.render_invoice_pdf(session, invoice=invoice, tenant=tenant)
    filename = invoice.invoice_number or "DRAFT"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )
