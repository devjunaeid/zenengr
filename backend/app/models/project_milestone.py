"""ProjectMilestone — instantiated copy of a MilestoneStepTemplate (FEAT-007)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import MilestoneStatus

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.project import Project
    from app.models.project_service import ProjectService


class ProjectMilestone(TimestampMixin, Base):
    __tablename__ = "project_milestones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("project_services.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("services.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MilestoneStatus] = mapped_column(
        default=MilestoneStatus.PENDING, nullable=False
    )
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    project: Mapped[Project] = relationship("Project", back_populates="milestones")
    project_service: Mapped[ProjectService] = relationship(
        "ProjectService", back_populates="milestones"
    )
    assignee: Mapped[AdminUser | None] = relationship("AdminUser")
