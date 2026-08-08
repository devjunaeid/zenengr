"""Pydantic schemas for client management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── Client CRUD ─────────────────────────────────────────────────────────────


class ClientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    client_type: str = Field(default="company", pattern="^(company|individual)$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    billing_address: dict[str, Any] | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None


class ClientUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    client_type: str | None = Field(default=None, pattern="^(company|individual)$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    billing_address: dict[str, Any] | None = None
    tax_id: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = None


class ClientUserSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    is_primary_billing_contact: bool


class ClientListItem(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    client_type: str
    email: str | None
    phone: str | None
    status: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    active_projects: int = 0
    total_invoiced: str = "0.00"
    total_outstanding: str = "0.00"


class ClientListResponse(BaseModel):
    items: list[ClientListItem]
    total: int
    page: int
    page_size: int


class ClientDetailResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    client_type: str
    email: str | None
    phone: str | None
    billing_address: dict[str, Any]
    tax_id: str | None
    status: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    client_users: list[ClientUserSummary]
    recent_activity: list[dict[str, Any]]
    total_invoiced: str = "0.00"
    total_paid: str = "0.00"
    total_outstanding: str = "0.00"


# ── Notes ────────────────────────────────────────────────────────────────────


class ClientNoteCreateRequest(BaseModel):
    body: str = Field(min_length=1)


class ClientNoteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    body: str
    author_id: uuid.UUID
    author_name: str | None = None
    created_at: datetime


class ClientNoteListResponse(BaseModel):
    items: list[ClientNoteResponse]
    total: int


# ── Activity ─────────────────────────────────────────────────────────────────


class ClientActivityEntry(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: str | None
    details: dict[str, Any]
    actor_id: uuid.UUID | None
    actor_type: str
    created_at: datetime


class ClientActivityResponse(BaseModel):
    items: list[ClientActivityEntry]
    total: int
    page: int
    page_size: int


# ── Tags ─────────────────────────────────────────────────────────────────────


class ClientTagsResponse(BaseModel):
    tags: list[str]


# ── Archive ──────────────────────────────────────────────────────────────────


class ClientArchiveResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: str
