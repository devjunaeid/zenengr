"""Pydantic schemas for tenant-facing APIs.

Profile, settings, plan/usage, feature flags, audit logs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubscriptionStatus, TenantStatus

# ── Tenant profile ──────────────────────────────────────────────────────────


class TenantProfileResponse(BaseModel):
    id: uuid.UUID
    business_name: str
    slug: str
    status: TenantStatus
    contact_info: dict[str, Any]
    branding: dict[str, Any]
    logo_url: str | None = None
    plan_name: str
    plan_id: uuid.UUID
    subscription_status: SubscriptionStatus | None = None

    model_config = {"from_attributes": True}


class TenantProfileUpdateRequest(BaseModel):
    business_name: str | None = Field(default=None, min_length=1, max_length=255)
    contact_info: dict[str, Any] | None = None
    branding: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


# ── Settings ────────────────────────────────────────────────────────────────


class TenantSettingItem(BaseModel):
    key: str
    value: str | None  # None when masked for tenant caller
    permission_level: str
    editable: bool

    model_config = {"from_attributes": True}


class TenantSettingUpdateRequest(BaseModel):
    value: str = Field(..., min_length=1, max_length=1024)


# ── Plan + usage ────────────────────────────────────────────────────────────


class PlanLimits(BaseModel):
    max_admin_users: int
    max_clients: int
    max_active_projects: int
    max_storage_mb: int


class UsageCounts(BaseModel):
    admin_users: int = 0
    clients: int = 0
    active_projects: int = 0
    storage_mb: float = 0.0


class TenantPlanResponse(BaseModel):
    plan_name: str
    limits: PlanLimits
    usage: UsageCounts


# ── Feature flags ───────────────────────────────────────────────────────────


class FeatureFlagItem(BaseModel):
    key: str
    enabled: bool


class FeatureFlagDetail(BaseModel):
    key: str
    enabled: bool
    source: str  # "override" | "plan_default" | "system_default"


class FeatureFlagOverrideUpdate(BaseModel):
    enabled: bool


class PlanFlagDefaultUpdate(BaseModel):
    enabled: bool


# ── Audit logs ──────────────────────────────────────────────────────────────


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    action: str
    actor_id: uuid.UUID | None = None
    actor_type: str
    entity_type: str
    entity_id: str | None = None
    details: dict[str, Any] = {}
    created_at: datetime
    actor_name: str | None = None
    entity_label: str | None = None

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
