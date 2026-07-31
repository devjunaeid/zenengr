"""ProjectService join entity (FEAT-007).

Links a Project to a Service. Carries its own status (active/cancelled)
and a price snapshot at attachment time.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import ProjectServiceStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.project_milestone import ProjectMilestone
    from app.models.service import Service


class ProjectService(TimestampMixin, Base):
    __tablename__ = "project_services"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "service_id",
            name="uq_project_services_project_id_service_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("services.id"), index=True, nullable=False
    )
    status: Mapped[ProjectServiceStatus] = mapped_column(
        default=ProjectServiceStatus.ACTIVE, nullable=False
    )
    price_at_attachment: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    project: Mapped[Project] = relationship("Project", back_populates="project_services")
    service: Mapped[Service] = relationship("Service")
    milestones: Mapped[list[ProjectMilestone]] = relationship(
        "ProjectMilestone",
        back_populates="project_service",
        cascade="all, delete-orphan",
        order_by="ProjectMilestone.sequence_order",
    )
