"""Pydantic schemas for user administration endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import AdminUserRole


class UserListItem(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: AdminUserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
