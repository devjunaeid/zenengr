"""Pydantic schemas for Super Admin platform APIs."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import BillingCycle, SubscriptionStatus, TenantStatus

# ── Plan schemas ────────────────────────────────────────────────────────────


class PlanCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=1024)
    max_admin_users: int = Field(..., ge=1)
    max_clients: int = Field(..., ge=1)
    max_active_projects: int = Field(..., ge=1)
    max_storage_mb: int = Field(..., ge=1)


class PlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    max_admin_users: int | None = Field(default=None, ge=1)
    max_clients: int | None = Field(default=None, ge=1)
    max_active_projects: int | None = Field(default=None, ge=1)
    max_storage_mb: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class PlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    max_admin_users: int
    max_clients: int
    max_active_projects: int
    max_storage_mb: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tenant_count: int = 0

    model_config = {"from_attributes": True}


# ── Tenant schemas ──────────────────────────────────────────────────────────


class TenantCreateRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    plan_id: uuid.UUID
    admin_email: EmailStr
    admin_full_name: str = Field(..., min_length=1, max_length=255)


class TenantCreateResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    slug: str
    status: TenantStatus
    plan_id: uuid.UUID
    admin_email: str
    temp_password: str

    model_config = {"from_attributes": True}


class SlugAvailableResponse(BaseModel):
    slug: str
    available: bool
    valid: bool


class TenantListItem(BaseModel):
    id: uuid.UUID
    business_name: str
    slug: str
    status: TenantStatus
    plan_name: str
    created_at: datetime
    active_user_count: int = 0

    model_config = {"from_attributes": True}


class TenantListResponse(BaseModel):
    items: list[TenantListItem]
    total: int
    page: int
    page_size: int


class TenantUpdateRequest(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_info: dict[str, Any] | None = None
    branding: dict[str, Any] | None = None
    logo_url: str | None = Field(default=None, max_length=2048)


class TenantSubscriptionInfo(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    renewal_date: date | None = None

    model_config = {"from_attributes": True}


class TenantSettingInfo(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


class TenantDetailResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    slug: str
    status: TenantStatus
    plan_id: uuid.UUID
    plan_name: str
    contact_info: dict[str, Any]
    branding: dict[str, Any]
    logo_url: str | None = None
    created_at: datetime
    updated_at: datetime
    subscription: TenantSubscriptionInfo | None = None
    settings: list[TenantSettingInfo] = []

    model_config = {"from_attributes": True}


# ── Subscription schemas ────────────────────────────────────────────────────


class SubscriptionViewResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    renewal_date: date | None = None
    plan_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionUpdateRequest(BaseModel):
    plan_id: uuid.UUID | None = None
    status: SubscriptionStatus | None = None
    billing_cycle: BillingCycle | None = None
    renewal_date: date | None = None
