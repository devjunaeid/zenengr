"""Client-portal data schemas (client invoice + client project portal endpoints).

Money fields are serialized as 2-decimal strings ("f2"); statuses are enum values.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import (
    InvoiceStatus,
    MilestoneStatus,
    ProjectServiceStatus,
    ProjectStatus,
)
from app.schemas.invoices import InvoiceLineItemResponse
from app.schemas.projects import LinkedInvoiceItem

# ── Client invoice list ──────────────────────────────────────────────────────


class ClientInvoiceListItem(BaseModel):
    id: uuid.UUID
    invoice_number: str | None
    status: InvoiceStatus
    project_id: uuid.UUID | None
    project_name: str
    issue_date: date | None
    due_date: date | None
    total: str
    created_at: datetime


class ClientInvoiceListResponse(BaseModel):
    items: list[ClientInvoiceListItem]
    total: int
    page: int
    page_size: int


# ── Client invoice detail ────────────────────────────────────────────────────


class ClientInvoiceDetailResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str | None
    status: InvoiceStatus
    project_id: uuid.UUID | None
    project_name: str
    issue_date: date | None
    due_date: date | None
    subtotal: str
    tax_total: str
    total: str
    notes: str
    paid_amount: str
    balance_due: str
    tenant_business_name: str | None = None
    tenant_logo_url: str | None = None
    line_items: list[InvoiceLineItemResponse]
    created_at: datetime
    updated_at: datetime


# ── Client formatting settings ───────────────────────────────────────────────


class ClientSettingsResponse(BaseModel):
    currency: str
    timezone: str
    date_format: str
    time_format: str


# ── Client project list ──────────────────────────────────────────────────────


class ClientProjectListItem(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    start_date: date | None
    milestone_total: int
    milestone_completed: int
    milestone_completion_pct: float
    created_at: datetime


class ClientProjectListResponse(BaseModel):
    items: list[ClientProjectListItem]
    total: int
    page: int
    page_size: int


# ── Client project detail ────────────────────────────────────────────────────


class ClientProjectServiceItem(BaseModel):
    id: uuid.UUID
    service_name: str
    status: ProjectServiceStatus
    price_at_attachment: str | None


class ClientProjectMilestoneItem(BaseModel):
    id: uuid.UUID
    name: str
    sequence_order: int
    status: MilestoneStatus
    planned_date: date | None
    actual_date: date | None
    assignee_id: uuid.UUID | None


class ClientProjectFinancialSummary(BaseModel):
    total_invoiced: str = "0.00"
    total_paid: str = "0.00"
    balance_due: str = "0.00"


class ClientProjectDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    start_date: date | None
    client_id: uuid.UUID
    milestone_total: int
    milestone_completed: int
    milestone_completion_pct: float
    services: list[ClientProjectServiceItem]
    milestones: list[ClientProjectMilestoneItem]
    financials: ClientProjectFinancialSummary
    linked_invoices: list[LinkedInvoiceItem]
