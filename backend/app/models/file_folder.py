"""FileFolder model (FEAT-012, TODO-123/124/125/137).

Tenant-scoped folder tree. Root folders (per scope) are provisioned lazily
by the files service; project subfolders hang off the "Project files" root.
created_by_id/created_by_type record the actor polymorphically
("admin_user" | "client_user").
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import FileScope


class FileFolder(TimestampMixin, Base):
    __tablename__ = "file_folders"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "parent_id",
            "scope",
            "name",
            "project_id",
            name="uq_file_folders_tenant_parent_scope_name_project",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("file_folders.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[FileScope] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_by_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,  # "admin_user" | "client_user"
    )
