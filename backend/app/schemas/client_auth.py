"""Pydantic schemas for client portal auth endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class ClientLoginRequest(BaseModel):
    email: EmailStr
    password: str


class ClientUserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str = "client_user"
    client_id: str
    tenant_id: str

    model_config = {"from_attributes": True}


class ClientLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: ClientUserResponse


class ClientMeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str = "client_user"
    client_id: str
    tenant_id: str
    client: ClientSummary


class ClientSummary(BaseModel):
    name: str
    status: str


class ClientInviteLookupResponse(BaseModel):
    email: str
    client_name: str
    tenant_name: str
    expires_at: datetime


class ClientRegisterRequest(BaseModel):
    token: str
    full_name: str
    password: str


class ClientInviteResponse(BaseModel):
    id: UUID
    email: str
    expires_at: datetime
    accepted_at: datetime | None = None
    status: str  # pending | accepted | expired

    model_config = {"from_attributes": True}


class ClientInviteCreateRequest(BaseModel):
    email: EmailStr
