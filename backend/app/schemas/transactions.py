"""Pydantic schemas for invoice transaction endpoints.

FEAT-009 (TODO-089/090/092/093/094) + FEAT-015 (refunds/advances/ledger).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, TransactionDirection


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


class RefundRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    method: PaymentMethod | None = None  # default: other
    reference_note: str | None = None
    model_config = {"extra": "forbid"}


class ApplyAdvanceRequest(BaseModel):
    # None = apply as much as the advance balance + invoice balance allow.
    amount: Decimal | None = Field(default=None, gt=0)
    model_config = {"extra": "forbid"}


class ApplyAdvanceResponse(BaseModel):
    applied: str
    advance_balance: str


class PaymentAllocationResponse(BaseModel):
    id: uuid.UUID
    line_item_id: uuid.UUID
    amount: str


class TransactionResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: str
    direction: TransactionDirection
    method: PaymentMethod
    reference_note: str
    recorded_by_id: uuid.UUID | None
    recorded_at: datetime
    allocations: list[PaymentAllocationResponse]


class LedgerEntry(BaseModel):
    id: uuid.UUID
    kind: str
    amount: str
    reference: str
    invoice_id: uuid.UUID | None
    created_at: datetime
    running_balance: str


class ClientLedgerResponse(BaseModel):
    advance_balance: str
    entries: list[LedgerEntry]
