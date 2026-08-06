"""Pydantic schemas for project comment endpoints (FEAT-010, TODO-100/103/104/106/107)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import CommentAuthorType


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    is_internal: bool = False
    model_config = {"extra": "forbid"}


class CommentEditRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    model_config = {"extra": "forbid"}


class CommentResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    author_id: uuid.UUID
    author_type: CommentAuthorType
    author_name: str
    content: str
    is_internal: bool
    created_at: datetime
