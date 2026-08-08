"""Pydantic schemas for self-service account endpoints (FEAT-011)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import NotificationChannel, NotificationEventType


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)
    phone: str | None = Field(default=None, max_length=50)
    timezone: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=10)
    email: EmailStr | None = Field(default=None)

    model_config = {"extra": "forbid"}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    model_config = {"extra": "forbid"}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ClientResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ActivityResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    description: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


class NotificationPreferenceEntry(BaseModel):
    event_type: NotificationEventType
    enabled: bool


class NotificationPreferencesUpdateRequest(BaseModel):
    preferences: list[NotificationPreferenceEntry]
    channel: NotificationChannel = NotificationChannel.EMAIL

    model_config = {"extra": "forbid"}


class NotificationPreferenceResponse(BaseModel):
    event_type: NotificationEventType
    enabled: bool


class VerifyEmailRequest(BaseModel):
    token: str
