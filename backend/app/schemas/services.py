"""Pydantic schemas for service catalog management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ── Milestone steps ─────────────────────────────────────────────────────────


class MilestoneStepInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sequence_order: int = Field(ge=1)
    expected_duration_days: int | None = Field(default=None, ge=1)
    description: str = Field(default="", max_length=10_000)


class MilestoneStepResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    sequence_order: int
    expected_duration_days: int | None
    description: str
    created_at: datetime
    updated_at: datetime


# ── Service CRUD ────────────────────────────────────────────────────────────


class ServiceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10_000)
    default_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
    )
    steps: list[MilestoneStepInput] = Field(default_factory=list)


class ServiceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    default_price: Decimal | None = Field(default=None, ge=Decimal("0"))
    is_active: bool | None = None
    steps: list[MilestoneStepInput] | None = None


class ServiceListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str
    default_price: Decimal | None
    is_active: bool
    step_count: int
    created_at: datetime
    updated_at: datetime


class ServiceListResponse(BaseModel):
    items: list[ServiceListItem]
    total: int
    page: int
    page_size: int


class ServiceDetailResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    description: str
    default_price: Decimal | None
    is_active: bool
    step_count: int
    in_use: bool = False
    project_count: int = 0
    created_at: datetime
    updated_at: datetime
    steps: list[MilestoneStepResponse]
