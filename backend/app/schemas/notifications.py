"""Pydantic schemas for notification endpoints (FEAT-017, TODO-172)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import NotificationEventType


class NotificationItem(BaseModel):
    id: uuid.UUID
    event_type: NotificationEventType
    title: str
    body: str
    entity_type: str | None
    entity_id: str | None
    data: dict[str, Any]
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int
    unread: int
    page: int
    page_size: int


class UnreadCountResponse(BaseModel):
    count: int
