"""Pydantic schemas for per-tenant SMTP config (FEAT-013)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import SmtpSecurityMode


class TenantSmtpConfigUpdateRequest(BaseModel):
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=255)
    clear_password: bool | None = None
    from_email: EmailStr | None = None
    from_name: str | None = Field(default=None, max_length=255)
    mode: SmtpSecurityMode | None = None
    enabled: bool | None = None

    model_config = {"extra": "forbid"}


class TenantSmtpConfigResponse(BaseModel):
    host: str | None
    port: int | None
    username: str | None
    from_email: str | None
    from_name: str | None
    mode: SmtpSecurityMode
    enabled: bool
    has_password: bool


class SmtpTestRequest(BaseModel):
    to_email: EmailStr | None = None
