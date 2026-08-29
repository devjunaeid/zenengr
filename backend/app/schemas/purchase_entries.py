"""Pydantic schemas for purchase entry endpoints."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class PurchaseEntryItemInput(BaseModel):
    item_date: date | None = None
    description: str
    quantity: Decimal = Decimal("1")
    rate: Decimal

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v

    @field_validator("rate")
    @classmethod
    def rate_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("rate must be >= 0")
        return v


class PurchaseEntryCreateRequest(BaseModel):
    title: str | None = None
    notes: str | None = None
    entry_date: date | None = None
    items: list[PurchaseEntryItemInput] = []
    model_config = {"extra": "forbid"}


class PurchaseEntryItemUpdateInput(BaseModel):
    id: uuid.UUID | None = None  # existing item id; None = new row
    item_date: date | None = None
    description: str | None = None
    quantity: Decimal | None = None
    rate: Decimal | None = None

    @field_validator("quantity")
    @classmethod
    def qty_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("quantity must be > 0")
        return v

    @field_validator("rate")
    @classmethod
    def rate_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("rate must be >= 0")
        return v


class PurchaseEntryUpdateRequest(BaseModel):
    title: str | None = None
    notes: str | None = None
    entry_date: date | None = None
    items: list[PurchaseEntryItemUpdateInput] | None = None
    model_config = {"extra": "forbid"}


# ── Response schemas ────────────────────────────────────────────────────────


class PurchaseEntryItemResponse(BaseModel):
    id: uuid.UUID
    item_date: date | None
    description: str
    quantity: str
    rate: str
    total: str


class PurchaseEntryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    notes: str
    entry_date: date | None
    grand_total: str
    created_by_id: uuid.UUID | None
    items: list[PurchaseEntryItemResponse]
    created_at: datetime
    updated_at: datetime


class PurchaseEntryListItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    entry_date: date | None
    grand_total: str
    item_count: int
    created_at: datetime


class PurchaseEntryListResponse(BaseModel):
    items: list[PurchaseEntryListItem]
    total: int
    page: int
    page_size: int
