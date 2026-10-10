"""API endpoints for unified Payments engine (FEAT-027, TODO-222)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.schemas.payments import (
    PaymentCreateRequest,
    PaymentResponse,
    PaymentUpdateRequest,
    PaymentVoidRequest,
)
from app.services.payments import (
    list_project_payments,
    payment_to_response,
    record_payment,
    restore_payment,
    update_payment,
    void_payment,
)

router = APIRouter(tags=["payments"])


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


@router.post(
    "/tenant/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment(
    body: PaymentCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PaymentResponse:
    """Record a payment (Money In) across project and invoices."""
    tenant_id = _get_tenant_id(user)

    payment = await record_payment(
        session,
        tenant_id=tenant_id,
        client_id=body.client_id,
        project_id=body.project_id,
        amount=body.amount,
        method=body.method,
        paid_on=body.paid_on,
        reference_note=body.reference_note,
        notes=body.notes,
        actor_id=user.id,
        auto_allocate=body.auto_allocate,
        invoice_id=body.invoice_id,
        allocations=body.allocations,
    )
    return await payment_to_response(session, payment)


@router.post(
    "/tenant/projects/{project_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project_payment(
    project_id: str,
    body: PaymentCreateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PaymentResponse:
    """Record a payment (Money In) on a project."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")

    payment = await record_payment(
        session,
        tenant_id=tenant_id,
        client_id=body.client_id,
        project_id=pid,
        amount=body.amount,
        method=body.method,
        paid_on=body.paid_on,
        reference_note=body.reference_note,
        notes=body.notes,
        actor_id=user.id,
        auto_allocate=body.auto_allocate,
        invoice_id=body.invoice_id,
        allocations=body.allocations,
    )
    return await payment_to_response(session, payment)


@router.get(
    "/tenant/projects/{project_id}/payments",
    response_model=list[PaymentResponse],
)
async def get_project_payments(
    project_id: str,
    include_voided: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(get_current_admin_user),
) -> list[PaymentResponse]:
    """List payments for a project."""
    tenant_id = _get_tenant_id(user)
    pid = _parse_uuid(project_id, kind="Project")
    payments = await list_project_payments(
        session,
        tenant_id=tenant_id,
        project_id=pid,
        include_voided=include_voided,
    )
    return [await payment_to_response(session, p) for p in payments]


@router.patch(
    "/tenant/payments/{payment_id}",
    response_model=PaymentResponse,
)
async def patch_payment(
    payment_id: str,
    body: PaymentUpdateRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PaymentResponse:
    """Update payment fields. Flexible per ADR-004."""
    tenant_id = _get_tenant_id(user)
    pay_id = _parse_uuid(payment_id, kind="Payment")
    payment = await update_payment(
        session,
        tenant_id=tenant_id,
        payment_id=pay_id,
        amount=body.amount,
        method=body.method,
        paid_on=body.paid_on,
        reference_note=body.reference_note,
        notes=body.notes,
        actor_id=user.id,
    )
    return await payment_to_response(session, payment)


@router.post(
    "/tenant/payments/{payment_id}/void",
    response_model=PaymentResponse,
)
async def post_void_payment(
    payment_id: str,
    body: PaymentVoidRequest,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PaymentResponse:
    """Soft-delete (void) a payment with an optional reason per ADR-004."""
    tenant_id = _get_tenant_id(user)
    pay_id = _parse_uuid(payment_id, kind="Payment")
    payment = await void_payment(
        session,
        tenant_id=tenant_id,
        payment_id=pay_id,
        reason=body.reason,
        actor_id=user.id,
    )
    return await payment_to_response(session, payment)


@router.post(
    "/tenant/payments/{payment_id}/restore",
    response_model=PaymentResponse,
)
async def post_restore_payment(
    payment_id: str,
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("manage", "projects")),
) -> PaymentResponse:
    """Restore a previously voided payment per ADR-004."""
    tenant_id = _get_tenant_id(user)
    pay_id = _parse_uuid(payment_id, kind="Payment")
    payment = await restore_payment(
        session,
        tenant_id=tenant_id,
        payment_id=pay_id,
        actor_id=user.id,
    )
    return await payment_to_response(session, payment)
