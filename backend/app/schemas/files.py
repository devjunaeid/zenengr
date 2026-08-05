"""Pydantic schemas for tenant file endpoints (FEAT-012, TODO-127/128/129/130/131/136)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import FileScope


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    scope: FileScope
    project_id: uuid.UUID | None = None
    model_config = {"extra": "forbid"}


class FolderRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    model_config = {"extra": "forbid"}


class FolderItem(BaseModel):
    id: uuid.UUID
    name: str
    scope: FileScope
    parent_id: uuid.UUID | None
    project_id: uuid.UUID | None
    created_at: datetime


class FolderTreeNode(BaseModel):
    id: uuid.UUID | None  # None = virtual "My files" root (no DB row)
    name: str
    scope: FileScope
    project_id: uuid.UUID | None
    children: list[FolderTreeNode] = []


class FileAssetItem(BaseModel):
    id: uuid.UUID
    name: str
    scope: FileScope
    folder_id: uuid.UUID | None
    project_id: uuid.UUID | None
    content_type: str
    size_bytes: int
    sha256: str
    created_by_id: uuid.UUID
    created_by_type: str
    created_at: datetime


class FileListResponse(BaseModel):
    items: list[FileAssetItem]
    total: int
    page: int
    page_size: int


class FileRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    model_config = {"extra": "forbid"}


class FileMoveRequest(BaseModel):
    folder_id: uuid.UUID | None = None  # None = scope root (no folder)
    model_config = {"extra": "forbid"}
