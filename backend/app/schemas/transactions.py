"""Pydantic schemas for invoice transaction endpoints (FEAT-009, TODO-089/090/092/093/094)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod


class AllocationInput(BaseModel):
    line_item_id: uuid.UUID
    amount: Decimal


class TransactionCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    method: PaymentMethod
    reference_note: str | None = None
    recorded_at: datetime | None = None  # default: now
    # Manual override (TODO-094); None = auto proportional allocation.
    allocations: list[AllocationInput] | None = None
    model_config = {"extra": "forbid"}


class PaymentAllocationResponse(BaseModel):
    id: uuid.UUID
    line_item_id: uuid.UUID
    amount: str


class TransactionResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: str
    method: PaymentMethod
    reference_note: str
    recorded_by_id: uuid.UUID | None
    recorded_at: datetime
    allocations: list[PaymentAllocationResponse]
