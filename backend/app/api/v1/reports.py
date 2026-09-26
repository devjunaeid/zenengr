"""Company global ledger & analytics reporting endpoints (FEAT-025, TODO-213).

Base path: /api/v1/tenant/reports
Guard: view/financial_reports (Admin and Manager only). Read-only.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_permission
from app.db.session import get_session
from app.models.admin_user import AdminUser
from app.schemas.reports import CompanyLedgerResponse
from app.services import reports as reports_service

router = APIRouter(prefix="/tenant/reports", tags=["reports"])


def _get_tenant_id(user: AdminUser) -> uuid.UUID:
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must belong to a tenant",
        )
    return user.tenant_id


def _parse_uuid(value: str | None, *, field_name: str) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be a valid UUID",
        ) from exc


@router.get("/company-ledger", response_model=CompanyLedgerResponse)
async def get_company_ledger_endpoint(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    client_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    granularity: str = Query(default="month", pattern="^(month|day)$"),
    tab: str = Query(default="all", pattern="^(all|timeline|projects|clients)$"),
    session: AsyncSession = Depends(get_session),
    user: AdminUser = Depends(require_permission("view", "financial_reports")),
) -> CompanyLedgerResponse:
    """Company-wide executive ledger, KPI summary, and multi-dimensional analytics.

    Admin and Manager only. Read-only.
    """
    tenant_id = _get_tenant_id(user)
    parsed_client_id = _parse_uuid(client_id, field_name="client_id")
    parsed_project_id = _parse_uuid(project_id, field_name="project_id")

    data = await reports_service.get_company_ledger(
        session,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        client_id=parsed_client_id,
        project_id=parsed_project_id,
        granularity=granularity,
        tab=tab,
    )
    return CompanyLedgerResponse(**data)
