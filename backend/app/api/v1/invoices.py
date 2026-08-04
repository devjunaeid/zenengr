"""Tenant-scoped invoice endpoints (FEAT-008, TODO-075/076/078/079).

Base path: /api/v1/tenant/invoices
Guards: manage/invoices = admin+manager for writes; all staff can read.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.models.enums import InvoiceStatus
from app.models.tenant import Tenant
from app.schemas.invoices import (
    InvoiceCreateRequest,
    InvoiceLineItemResponse,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdateRequest,
)
from app.schemas.transactions import (
    PaymentAllocationResponse,
    TransactionCreateRequest,
    TransactionResponse,
)
from app.services import invoices as invoice_service
from app.services import pdf as pdf_service
from app.services import transactions as transaction_service

router = APIRouter(prefix="/tenant/invoices", tags=["invoices"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _parse_uuid(value: str, *, kind: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{kind} not found",
        ) from exc


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


def _to_response(invoice: Any) -> InvoiceResponse:
    items = sorted(invoice.line_items, key=lambda li: li.created_at)
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        project_id=invoice.project_id,
        client_id=invoice.project.client_id,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        subtotal=f"{invoice.subtotal:.2f}",
        tax_total=f"{invoice.tax_total:.2f}",
        total=f"{invoice.total:.2f}",
        notes=invoice.notes,
        line_items=[_to_line_item_response(li) for li in items],
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
    )


def _to_transaction_response(tx: Any) -> TransactionResponse:
    allocations = sorted(tx.allocations, key=lambda a: a.created_at)
    return TransactionResponse(
        id=tx.id,
        invoice_id=tx.invoice_id,
        amount=f"{tx.amount:.2f}",
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


# ═══════════════════════════════════════════════════════════════════════════
# CRUD
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice_endpoint(
    body: InvoiceCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "invoices")),
) -> InvoiceResponse:
    """Create a draft invoice. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    invoice = await invoice_service.create_draft_invoice(
        session,
        tenant_id=tenant_id,
        project_id=body.project_id,
        issue_date=body.issue_date,
        due_date=body.due_date,
        notes=body.notes,
        line_items=body.line_items,
        actor_id=user.id,
    )
    return _to_response(invoice)


@router.get("/", response_model=InvoiceListResponse)
async def list_invoices_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_val: str | None = Query(default=None, alias="status"),
    project_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> InvoiceListResponse:
    """List invoices for a tenant. All staff can read."""
    tenant_id = _get_tenant_id(user)

    status_filter: InvoiceStatus | None = None
    if status_val:
        try:
            status_filter = InvoiceStatus(status_val)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Invalid status: {status_val}. "
                    "Must be 'draft', 'issued', 'partially_paid', 'paid', or 'void'."
                ),
            ) from None

    parsed_project_id: uuid.UUID | None = None
    if project_id:
        try:
            parsed_project_id = uuid.UUID(project_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="project_id must be a valid UUID",
            ) from exc

    result = await invoice_service.list_invoices(
        session,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        project_id=parsed_project_id,
    )
    items = [InvoiceListItem(**item) for item in result["items"]]
    return InvoiceListResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> InvoiceResponse:
    """Get invoice detail with line items. All staff can read."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    invoice = await invoice_service.get_invoice(session, tenant_id=tenant_id, invoice_id=iid)
    return _to_response(invoice)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> Response:
    """Render an invoice as a PDF attachment (TODO-084/085). All staff can read."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    invoice = await invoice_service.get_invoice(session, tenant_id=tenant_id, invoice_id=iid)
    tenant = await session.get(Tenant, tenant_id)
    pdf_bytes = await pdf_service.render_invoice_pdf(session, invoice=invoice, tenant=tenant)
    filename = invoice.invoice_number or "DRAFT"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )


@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice_endpoint(
    invoice_id: str,
    body: InvoiceUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "invoices")),
) -> InvoiceResponse:
    """Update a draft invoice (or notes on an issued one). Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    invoice = await invoice_service.update_draft_invoice(
        session,
        tenant_id=tenant_id,
        invoice_id=iid,
        issue_date=body.issue_date,
        due_date=body.due_date,
        notes=body.notes,
        line_items=body.line_items,
        actor_id=user.id,
    )
    return _to_response(invoice)


@router.delete(
    "/{invoice_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_invoice_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "invoices")),
) -> Response:
    """Delete a draft invoice. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    try:
        await invoice_service.delete_draft_invoice(
            session,
            tenant_id=tenant_id,
            invoice_id=iid,
            actor_id=user.id,
        )
    except invoice_service.InvoiceDeleteNotAllowedError:
        raise HTTPException(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Issued invoices cannot be deleted",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════════
# Issue (TODO-078)
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "invoices")),
) -> InvoiceResponse:
    """Issue a draft invoice: assign number + issue_date. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    invoice = await invoice_service.issue_invoice(
        session, tenant_id=tenant_id, invoice_id=iid, actor_id=user.id
    )
    return _to_response(invoice)


@router.post("/{invoice_id}/void", response_model=InvoiceResponse)
async def void_invoice_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "invoices")),
) -> InvoiceResponse:
    """Void an issued/partially-paid/paid invoice. Number + data retained. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    invoice = await invoice_service.void_invoice(
        session, tenant_id=tenant_id, invoice_id=iid, actor_id=user.id
    )
    return _to_response(invoice)


# ═══════════════════════════════════════════════════════════════════════════
# Transactions (FEAT-009, TODO-089/090/092/093/094)
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/{invoice_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_transaction_endpoint(
    invoice_id: str,
    body: TransactionCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "invoices")),
) -> TransactionResponse:
    """Record a payment against an issued/partially-paid invoice. Admin/Manager only."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    tx = await transaction_service.record_transaction(
        session,
        tenant_id=tenant_id,
        invoice_id=iid,
        amount=body.amount,
        method=body.method,
        reference_note=body.reference_note,
        recorded_at=body.recorded_at,
        allocations=body.allocations,
        actor_id=user.id,
    )
    return _to_transaction_response(tx)


@router.get(
    "/{invoice_id}/transactions",
    response_model=list[TransactionResponse],
)
async def list_transactions_endpoint(
    invoice_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[TransactionResponse]:
    """List payments recorded against an invoice. All staff can read."""
    tenant_id = _get_tenant_id(user)
    iid = _parse_uuid(invoice_id, kind="Invoice")
    txs = await transaction_service.list_transactions(session, tenant_id=tenant_id, invoice_id=iid)
    return [_to_transaction_response(tx) for tx in txs]
