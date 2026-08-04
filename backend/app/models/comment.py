"""Comment model (FEAT-010, TODO-100/103/104/106/107).

A Comment is project-scoped and polymorphic: author_id points at either
admin_users.id (tenant author) or client_users.id (client author), with
author_type + a denormalized author_name snapshot captured at write time.
is_internal=True marks tenant-only notes; client users never see them.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import CommentAuthorType

if TYPE_CHECKING:
    from app.models.project import Project


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # polymorphic: admin_users.id or client_users.id
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    author_type: Mapped[CommentAuthorType] = mapped_column(nullable=False)
    # snapshot at write
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project: Mapped[Project] = relationship("Project")
