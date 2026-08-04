"""Pydantic schemas for project management endpoints (FEAT-007)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MilestoneStatus, ProjectServiceStatus, ProjectStatus

# ── Project create / update ─────────────────────────────────────────────────


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_id: uuid.UUID
    start_date: date | None = None
    owner_id: uuid.UUID | None = None
    service_ids: list[uuid.UUID] = Field(default_factory=list)


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: ProjectStatus | None = None
    start_date: date | None = None
    owner_id: uuid.UUID | None = None


# ── List + detail responses ─────────────────────────────────────────────────


class ProjectListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    client_id: uuid.UUID
    status: ProjectStatus
    start_date: date | None
    owner_id: uuid.UUID | None
    service_count: int = 0
    milestone_total: int = 0
    milestone_completed: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int


class ProjectServiceItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    service_id: uuid.UUID
    service_name: str
    status: ProjectServiceStatus
    price_at_attachment: Decimal | None
    created_at: datetime
    updated_at: datetime


class ProjectMilestoneItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    project_service_id: uuid.UUID
    service_id: uuid.UUID
    name: str
    sequence_order: int
    status: MilestoneStatus
    planned_date: date | None
    actual_date: date | None
    assignee_id: uuid.UUID | None
    description: str
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    client_id: uuid.UUID
    status: ProjectStatus
    start_date: date | None
    owner_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    services: list[ProjectServiceItem]
    milestones: list[ProjectMilestoneItem]


class ProjectCreateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    client_id: uuid.UUID
    status: ProjectStatus
    start_date: date | None
    owner_id: uuid.UUID | None
    service_count: int
    milestone_count: int
    created_at: datetime


# ── Attach service ──────────────────────────────────────────────────────────


class AttachServiceRequest(BaseModel):
    service_id: uuid.UUID


class AttachServiceResponse(BaseModel):
    project_service_id: uuid.UUID
    service_id: uuid.UUID
    service_name: str
    milestone_count: int


# ── Milestone update ────────────────────────────────────────────────────────


class MilestoneUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MilestoneStatus | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    assignee_id: uuid.UUID | None = None


# ── Project overview (TODO-072) ──────────────────────────────────────────────


class LinkedInvoiceItem(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    number: str
    status: str
    total: str = "0.00"


class ProjectServiceFinancialItem(BaseModel):
    service_id: uuid.UUID | None
    service_name: str
    total_invoiced: str = "0.00"
    total_paid: str = "0.00"
    total_outstanding: str = "0.00"


class ProjectOverviewResponse(BaseModel):
    project_id: uuid.UUID
    name: str
    status: ProjectStatus
    milestone_total: int
    milestone_completed: int
    milestone_completion_pct: float
    total_invoiced: str = "0.00"
    total_paid: str = "0.00"
    balance_due: str = "0.00"
    linked_invoices: list[LinkedInvoiceItem] = []
    service_breakdown: list[ProjectServiceFinancialItem] = []
