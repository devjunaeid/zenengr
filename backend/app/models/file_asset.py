"""FileAsset model (FEAT-012, TODO-124/125/137).

One row per uploaded file. storage_key is the backend object key
(tenant-namespaced, e.g. `{tenant_id}/{scope}/...`); sha256 records content
hash for dedupe/integrity. folder_id is nullable so assets survive folder
deletion (SET NULL). created_by_id/created_by_type record the actor
polymorphically ("admin_user" | "client_user").
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import FileScope


class FileAsset(TimestampMixin, Base):
    __tablename__ = "file_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("file_folders.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    scope: Mapped[FileScope] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_by_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # "admin_user" | "client_user"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
