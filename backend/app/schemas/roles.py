"""Pydantic schemas for role management (FEAT-016, TODO-163)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RolePermissionInput(BaseModel):
    action: str
    resource: str
    granted: bool

    model_config = {"extra": "forbid"}


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    role_type: str = Field(default="user", max_length=32)
    permissions: list[RolePermissionInput] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[RolePermissionInput] | None = None

    model_config = {"extra": "forbid"}


class RolePermissionResponse(BaseModel):
    action: str
    resource: str
    granted: bool


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    role_type: str = "user"
    is_system: bool
    tenant_id: uuid.UUID | None
    permissions: list[RolePermissionResponse]


class PermissionCatalogItem(BaseModel):
    action: str
    resource: str
    label: str
    group: str


class UserRoleUpdateRequest(BaseModel):
    role_id: uuid.UUID

    model_config = {"extra": "forbid"}
