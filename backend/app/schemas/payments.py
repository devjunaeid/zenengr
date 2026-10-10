"""Pydantic schemas for the unified Payment engine (FEAT-027, TODO-222)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import PaymentKind, PaymentMethod


class PaymentAllocationItem(BaseModel):
    id: uuid.UUID
    line_item_id: uuid.UUID
    amount: str
    invoice_id: uuid.UUID | None = None
    invoice_number: str | None = None
    voided_at: datetime | None = None


class PaymentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    project_id: uuid.UUID | None
    kind: PaymentKind
    amount: str
    method: PaymentMethod
    paid_on: date
    reference_note: str
    notes: str
    allocated_amount: str
    unallocated_amount: str
    allocations: list[PaymentAllocationItem] = []
    voided_at: datetime | None = None
    void_reason: str = ""
    created_at: datetime

    @computed_field
    @property
    def is_voided(self) -> bool:
        return self.voided_at is not None


class PaymentAllocationCreate(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"))
    line_item_id: uuid.UUID | None = None


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=Decimal("0"))
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    paid_on: date | None = None
    reference_note: str = ""
    notes: str = ""
    project_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    auto_allocate: bool = True
    invoice_id: uuid.UUID | None = None
    allocations: list[PaymentAllocationCreate] = []


class PaymentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal | None = Field(default=None, gt=Decimal("0"))
    method: PaymentMethod | None = None
    paid_on: date | None = None
    reference_note: str | None = None
    notes: str | None = None


class PaymentVoidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = ""


class PaymentAllocateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_id: uuid.UUID
    amount: Decimal | None = Field(default=None, gt=Decimal("0"))
