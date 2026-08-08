"""Invoice business logic (FEAT-008, TODO-075/076/078/079).

Owns the orchestration of:
- Draft invoice creation with line item resolution (service-priced or custom)
- Draft update (field-level, or full line item replacement)
- Draft deletion (draft only; issued/void mapped to 405 by the router)
- Issue: assigns gapless per-tenant invoice numbers under a row lock
- Invoice list/detail with eager-loaded relations
"""

from __future__ import annotations

import re
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ActorType, InvoiceStatus
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.invoice_number_sequence import InvoiceNumberSequence
from app.models.project import Project
from app.models.project_service import ProjectService
from app.models.tenant import Tenant
from app.services.audit import log as audit_log
from app.services.notifications import notify_invoice_issued, safe_notify
from app.services.settings import DEFAULT_SETTINGS, get_tenant_setting_by_key

# ── Exceptions ──────────────────────────────────────────────────────────────


class InvoiceNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found",
        )


class InvoiceNotDraftError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only draft invoices can be modified",
        )


class InvoiceVoidError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Voided invoices cannot be modified",
        )


class InvoiceAlreadyIssuedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invoice already issued",
        )


class InvoiceProjectNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


class InvoiceLineItemError(HTTPException):
    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail
            or ("Each line item must specify a project service or a description with unit price"),
        )


class InvoiceEmptyError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invoice must have at least one line item",
        )


class InvoiceNoPriceError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Service has no price to invoice",
        )


class InvoiceDeleteNotAllowedError(HTTPException):
    """Raised when deleting an issued/void invoice; router maps this to 405."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            detail="Issued invoices cannot be deleted",
        )


class InvoiceVoidSourceError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only issued, partially paid, or paid invoices can be voided",
        )


class InvoiceAlreadyVoidError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invoice already voided",
        )


# ── Helpers ─────────────────────────────────────────────────────────────────

_SEQ_PAD_RE = re.compile(r"\{[sS][eE][qQ]:0(\d+)d\}")


def _money(value: Decimal) -> Decimal:
    """Round to 2 decimal places, half-up."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def _get_project_for_tenant(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> Project | None:
    stmt = select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_project_service_for_invoice(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID,
    project_service_id: uuid.UUID,
) -> ProjectService | None:
    """Fetch a project_service that belongs to the given project in the tenant."""
    stmt = (
        select(ProjectService)
        .options(selectinload(ProjectService.service))
        .join(Project, ProjectService.project_id == Project.id)
        .where(
            ProjectService.id == project_service_id,
            ProjectService.project_id == project_id,
            Project.tenant_id == tenant_id,
        )
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def _get_invoice_with_relations(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice | None:
    """Fetch an invoice with line_items + project eager-loaded, tenant-scoped."""
    stmt = (
        select(Invoice)
        .options(
            selectinload(Invoice.line_items),
            selectinload(Invoice.project),
        )
        .execution_options(populate_existing=True)
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def _resolve_line_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID | None,
    inputs: list[Any],
    existing_by_id: dict[uuid.UUID, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve raw line item inputs into snapshot dicts for InvoiceLineItem.

    - project_service_id set: snapshot service name + price (attachment price,
      falling back to service default_price; InvoiceNoPriceError if neither).
      Only valid when a project is present: project services cannot be priced
      on a GENERAL (project-less) invoice.
    - otherwise: custom line; description + unit_price required (existing
      values kept when replacing an item by id during updates).
    """
    existing_by_id = existing_by_id or {}
    resolved: list[dict[str, Any]] = []
    for item in inputs:
        if item.project_service_id is not None:
            if project_id is None:
                raise InvoiceLineItemError("Project service line items require a project")
            ps = await _get_project_service_for_invoice(
                session, tenant_id, project_id, item.project_service_id
            )
            if ps is None:
                raise InvoiceLineItemError()
            service = ps.service
            price = ps.price_at_attachment
            if price is None:
                price = service.default_price if service is not None else None
            if price is None:
                raise InvoiceNoPriceError()
            description = service.name if service is not None else ""
            unit_price = price
            service_id = ps.service_id
            project_service_id = ps.id
            quantity = item.quantity
        else:
            description = item.description
            unit_price = item.unit_price
            quantity = item.quantity
            service_id = None
            project_service_id = None
            existing_id = getattr(item, "id", None)
            if existing_id is not None and existing_id in existing_by_id:
                orig = existing_by_id[existing_id]
                if description is None:
                    description = orig.description
                if unit_price is None:
                    unit_price = orig.unit_price
                if quantity is None:
                    quantity = orig.quantity
            if not description or unit_price is None:
                raise InvoiceLineItemError()

        quantity = quantity if quantity is not None else Decimal("1")
        amount = _money(quantity * unit_price)
        resolved.append(
            {
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
                "service_id": service_id,
                "project_service_id": project_service_id,
            }
        )
    return resolved


def _format_invoice_number(template: str, next_number: int, *, tenant_prefix: str) -> str:
    """Render an invoice number from a format template."""
    if not template:
        template = "INV-{YYYY}-{SEQ:04d}"
    year = str(date.today().year)

    def _pad(match: re.Match[str]) -> str:
        width = int(match.group(1))
        return str(next_number).zfill(width)

    out = _SEQ_PAD_RE.sub(_pad, template)
    out = out.replace("{SEQ}", str(next_number)).replace("{seq}", str(next_number))
    out = out.replace("{YYYY}", year).replace("{year}", year)
    out = out.replace("{tenant_prefix}", tenant_prefix)
    return out


# ── CRUD ────────────────────────────────────────────────────────────────────


async def create_draft_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID | None,
    issue_date: date | None,
    due_date: date | None,
    notes: str | None,
    line_items: list[Any],
    actor_id: uuid.UUID,
) -> Invoice:
    """Create a draft invoice with resolved line item snapshots.

    A NULL project_id creates a GENERAL (internal) invoice: no project
    existence check, no client link, and only custom line items are allowed
    (project_service inputs are rejected by _resolve_line_items).
    """
    if project_id is not None:
        project = await _get_project_for_tenant(session, tenant_id, project_id)
        if project is None:
            raise InvoiceProjectNotFoundError()
    if not line_items:
        raise InvoiceEmptyError()

    resolved = await _resolve_line_items(
        session, tenant_id=tenant_id, project_id=project_id, inputs=line_items
    )
    subtotal = _money(sum(item["amount"] for item in resolved))

    invoice = Invoice(
        tenant_id=tenant_id,
        project_id=project_id,
        invoice_number=None,
        status=InvoiceStatus.DRAFT,
        issue_date=issue_date,
        due_date=due_date,
        subtotal=subtotal,
        tax_total=Decimal("0"),
        total=subtotal,
        notes=notes or "",
    )
    session.add(invoice)
    await session.flush()
    for data in resolved:
        session.add(InvoiceLineItem(invoice_id=invoice.id, **data))

    audit_details: dict[str, str] = {"total": str(subtotal)}
    if project_id is not None:
        audit_details["project_id"] = str(project_id)
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.created",
        entity_type="invoice",
        entity_id=str(invoice.id),
        details=audit_details,
    )
    await session.commit()
    return await get_invoice(session, tenant_id=tenant_id, invoice_id=invoice.id)


async def get_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
) -> Invoice:
    """Get invoice with line_items + project eager-loaded. 404 if not found."""
    invoice = await _get_invoice_with_relations(session, tenant_id, invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError()
    return invoice


async def list_invoices(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status_filter: InvoiceStatus | None = None,
    project_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """List invoices for a tenant with optional status/project filters."""
    query = (
        select(Invoice).options(selectinload(Invoice.project)).where(Invoice.tenant_id == tenant_id)
    )
    if status_filter is not None:
        query = query.where(Invoice.status == status_filter)
    if project_id is not None:
        query = query.where(Invoice.project_id == project_id)

    count_stmt = select(Invoice).where(Invoice.tenant_id == tenant_id)
    if status_filter is not None:
        count_stmt = count_stmt.where(Invoice.status == status_filter)
    if project_id is not None:
        count_stmt = count_stmt.where(Invoice.project_id == project_id)
    count_q = select(func.count()).select_from(count_stmt.subquery())
    total_result = await session.execute(count_q)
    total: int = total_result.scalar_one()

    query = query.order_by(Invoice.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    invoices = list(result.unique().scalars().all())

    items: list[dict[str, Any]] = []
    for inv in invoices:
        items.append(
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status,
                "project_id": inv.project_id,
                "client_id": inv.project.client_id if inv.project else None,
                "issue_date": inv.issue_date,
                "due_date": inv.due_date,
                "total": f"{inv.total:.2f}",
                "created_at": inv.created_at,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def update_draft_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    issue_date: date | None,
    due_date: date | None,
    notes: str | None,
    line_items: list[Any] | None,
    actor_id: uuid.UUID,
) -> Invoice:
    """Update a draft invoice. Non-draft invoices accept notes-only edits."""
    invoice = await _get_invoice_with_relations(session, tenant_id, invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError()
    if invoice.status == InvoiceStatus.VOID:
        raise InvoiceVoidError()

    if invoice.status != InvoiceStatus.DRAFT:
        # Issued/paid invoices: notes stay editable; everything else is locked.
        if issue_date is not None or due_date is not None or line_items is not None:
            raise InvoiceNotDraftError()
        if notes is None or notes == invoice.notes:
            return invoice
        invoice.notes = notes
        await audit_log(
            session,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=ActorType.ADMIN_USER,
            action="invoice.updated",
            entity_type="invoice",
            entity_id=str(invoice.id),
            details={"changed_keys": ["notes"]},
        )
        await session.commit()
        return await get_invoice(session, tenant_id=tenant_id, invoice_id=invoice_id)

    changed = False
    if issue_date is not None and invoice.issue_date != issue_date:
        invoice.issue_date = issue_date
        changed = True
    if due_date is not None and invoice.due_date != due_date:
        invoice.due_date = due_date
        changed = True
    if notes is not None and invoice.notes != notes:
        invoice.notes = notes
        changed = True
    if line_items is not None:
        await _replace_line_items(session, invoice, line_items)
        changed = True

    if not changed:
        return invoice

    audit_details: dict[str, Any] = {}
    if invoice.project_id is not None:
        audit_details["project_id"] = str(invoice.project_id)
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.updated",
        entity_type="invoice",
        entity_id=str(invoice.id),
        details=audit_details,
    )
    await session.commit()
    return await get_invoice(session, tenant_id=tenant_id, invoice_id=invoice_id)


async def _replace_line_items(
    session: AsyncSession,
    invoice: Invoice,
    inputs: list[Any],
) -> None:
    """Delete existing line items and re-add from inputs; recompute totals."""
    existing = {li.id: li for li in invoice.line_items}
    for li in invoice.line_items:
        await session.delete(li)
    await session.flush()

    resolved = await _resolve_line_items(
        session,
        tenant_id=invoice.tenant_id,
        project_id=invoice.project_id,
        inputs=inputs,
        existing_by_id=existing,
    )
    subtotal = _money(sum(item["amount"] for item in resolved))
    invoice.subtotal = subtotal
    invoice.tax_total = Decimal("0")
    invoice.total = subtotal
    for data in resolved:
        session.add(InvoiceLineItem(invoice_id=invoice.id, **data))
    await session.flush()


async def delete_draft_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    """Hard-delete a draft invoice. Issued/void raise for router 405 mapping."""
    invoice = await _get_invoice_with_relations(session, tenant_id, invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError()
    if invoice.status != InvoiceStatus.DRAFT:
        raise InvoiceDeleteNotAllowedError()

    audit_details: dict[str, Any] = {}
    if invoice.project_id is not None:
        audit_details["project_id"] = str(invoice.project_id)
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.deleted",
        entity_type="invoice",
        entity_id=str(invoice.id),
        details=audit_details,
    )
    await session.delete(invoice)
    await session.commit()


# ── Issue ───────────────────────────────────────────────────────────────────


async def issue_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Invoice:
    """Issue a draft invoice: assign number, set issue_date, mark ISSUED."""
    invoice = await _get_invoice_with_relations(session, tenant_id, invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError()
    if invoice.status == InvoiceStatus.VOID:
        raise InvoiceVoidError()
    if invoice.status != InvoiceStatus.DRAFT:
        raise InvoiceAlreadyIssuedError()

    setting = await get_tenant_setting_by_key(session, tenant_id, "invoice_number_format")
    fmt: str | None = setting.value if setting is not None else None
    if not fmt:
        for entry in DEFAULT_SETTINGS:
            if entry["key"] == "invoice_number_format":
                fmt = entry["value"]
                break

    number = await generate_invoice_number(session, tenant_id=tenant_id, format_template=fmt or "")
    if invoice.issue_date is None:
        invoice.issue_date = date.today()
    invoice.invoice_number = number
    invoice.status = InvoiceStatus.ISSUED

    issue_details: dict[str, str] = {"invoice_number": number}
    if invoice.project_id is not None:
        issue_details["project_id"] = str(invoice.project_id)
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.issued",
        entity_type="invoice",
        entity_id=str(invoice.id),
        details=issue_details,
    )
    await session.commit()
    await safe_notify(notify_invoice_issued(session, invoice_id=invoice.id))
    return await get_invoice(session, tenant_id=tenant_id, invoice_id=invoice_id)


# ── Void (TODO-081) ─────────────────────────────────────────────────────────


async def void_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    invoice_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Invoice:
    """Void an issued, partially paid, or paid invoice (TODO-081).

    The invoice number and all line-item data are retained; only the status
    flips to VOID. Drafts are deleted, not voided, so they raise.
    """
    invoice = await _get_invoice_with_relations(session, tenant_id, invoice_id)
    if invoice is None:
        raise InvoiceNotFoundError()
    if invoice.status == InvoiceStatus.VOID:
        raise InvoiceAlreadyVoidError()
    if invoice.status == InvoiceStatus.DRAFT:
        raise InvoiceVoidSourceError()

    invoice.status = InvoiceStatus.VOID
    await audit_log(
        session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        actor_type=ActorType.ADMIN_USER,
        action="invoice.voided",
        entity_type="invoice",
        entity_id=str(invoice.id),
        details={"invoice_number": invoice.invoice_number or ""},
    )
    await session.commit()
    return await get_invoice(session, tenant_id=tenant_id, invoice_id=invoice_id)


# ── Number generation (TODO-079) ───────────────────────────────────────────


async def generate_invoice_number(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    format_template: str,
) -> str:
    """Lock + increment + format the tenant's invoice number sequence.

    Uses SELECT ... FOR UPDATE so concurrent issues cannot collide. If the
    tenant's row does not exist it is inserted; on a primary-key race the
    transaction is rolled back and the winning row is re-locked.
    """
    slug_stmt = select(Tenant.slug).where(Tenant.id == tenant_id)
    slug = (await session.execute(slug_stmt)).scalar_one_or_none()
    tenant_prefix = (slug or "TENANT").upper()

    stmt = (
        select(InvoiceNumberSequence)
        .where(InvoiceNumberSequence.tenant_id == tenant_id)
        .with_for_update()
    )
    seq = (await session.execute(stmt)).scalar_one_or_none()
    if seq is None:
        seq = InvoiceNumberSequence(
            tenant_id=tenant_id,
            last_number=0,
            format_template=format_template,
        )
        session.add(seq)
        try:
            await session.flush()
        except IntegrityError:
            # Another request inserted the row first; re-lock the winner.
            await session.rollback()
            seq = (await session.execute(stmt)).scalar_one_or_none()
            if seq is None:
                raise InvoiceNotFoundError() from None

    next_number = seq.last_number + 1
    seq.last_number = next_number
    seq.format_template = format_template
    await session.flush()
    return _format_invoice_number(format_template, next_number, tenant_prefix=tenant_prefix)
