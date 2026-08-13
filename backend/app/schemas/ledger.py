"""Pydantic schemas for the project ledger endpoints (FEAT-018, TODO-180/181/182).

Ledger entries carry f2-formatted string amounts (SIGNED for charges;
payments positive, refunds negative - the FE renders). The summary is the
live FR-18.4 math.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DiscountType, LedgerEntryType, LedgerSourceType


class LedgerEntryResponse(BaseModel):
    id: uuid.UUID
    type: LedgerEntryType
    amount: str
    description: str
    source_type: LedgerSourceType | None
    source_id: uuid.UUID | None
    invoice_ref: uuid.UUID | None
    invoice_number: str | None
    entry_date: date
    created_at: datetime


class SummaryResponse(BaseModel):
    subtotal: str
    discount_type: DiscountType | None
    discount_value: str | None
    discount_amount: str
    total: str
    paid: str
    due: str


class ProjectLedgerResponse(BaseModel):
    entries: list[LedgerEntryResponse]
    summary: SummaryResponse


class DiscountResponse(BaseModel):
    discount_type: DiscountType | None
    discount_value: str | None


class DiscountUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discount_type: DiscountType | None = None
    discount_value: Decimal | None = None


class AdjustmentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    description: str = Field(min_length=1, max_length=500)
