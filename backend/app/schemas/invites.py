"""Pydantic schemas for invite endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.models.enums import InviteRole


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: InviteRole

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.lower().strip()


class InviteResponse(BaseModel):
    id: UUID
    email: str
    role: InviteRole
    expires_at: datetime
    accepted_at: datetime | None = None
    status: str  # pending | accepted | expired

    model_config = {"from_attributes": True}


class InviteLookupResponse(BaseModel):
    email: str
    role: InviteRole
    tenant_name: str
    expires_at: datetime


class RegisterRequest(BaseModel):
    token: str
    full_name: str
    password: str
