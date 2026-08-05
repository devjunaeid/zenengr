"""Pydantic schemas for invoice endpoints (FEAT-008, TODO-075/076/078)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import InvoiceStatus


class InvoiceLineItemInput(BaseModel):
    project_service_id: uuid.UUID | None = None
    description: str | None = None
    unit_price: Decimal | None = None
    quantity: Decimal | None = None


class InvoiceCreateRequest(BaseModel):
    project_id: uuid.UUID | None = None
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    line_items: list[InvoiceLineItemInput] = []
    model_config = {"extra": "forbid"}


class InvoiceLineItemUpdateInput(BaseModel):
    id: uuid.UUID | None = None  # id of existing item to replace; None = new
    project_service_id: uuid.UUID | None = None
    description: str | None = None
    unit_price: Decimal | None = None
    quantity: Decimal | None = None


class InvoiceUpdateRequest(BaseModel):
    issue_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    line_items: list[InvoiceLineItemUpdateInput] | None = None
    model_config = {"extra": "forbid"}


class InvoiceLineItemResponse(BaseModel):
    id: uuid.UUID
    description: str
    quantity: str
    unit_price: str
    amount: str
    service_id: uuid.UUID | None
    project_service_id: uuid.UUID | None


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str | None
    status: InvoiceStatus
    project_id: uuid.UUID | None
    client_id: uuid.UUID | None
    is_general: bool
    issue_date: date | None
    due_date: date | None
    subtotal: str
    tax_total: str
    total: str
    notes: str
    line_items: list[InvoiceLineItemResponse]
    created_at: datetime
    updated_at: datetime


class InvoiceListItem(BaseModel):
    id: uuid.UUID
    invoice_number: str | None
    status: InvoiceStatus
    project_id: uuid.UUID | None
    client_id: uuid.UUID | None
    issue_date: date | None
    due_date: date | None
    total: str
    created_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int
    page: int
    page_size: int
