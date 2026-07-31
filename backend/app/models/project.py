"""Project model (FEAT-007).

A Project bundles one or more services for a specific client. Each attached
service becomes a ProjectService (join entity) that instantiates its
MilestoneStepTemplate as ProjectMilestone rows.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.client import Client
    from app.models.project_milestone import ProjectMilestone
    from app.models.project_service import ProjectService
    from app.models.tenant import Tenant


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id"), index=True, nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        default=ProjectStatus.DRAFT, nullable=False
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id"), nullable=True
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="projects")
    client: Mapped[Client] = relationship("Client", back_populates="projects")
    owner: Mapped[AdminUser | None] = relationship("AdminUser")
    project_services: Mapped[list[ProjectService]] = relationship(
        "ProjectService",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    milestones: Mapped[list[ProjectMilestone]] = relationship(
        "ProjectMilestone",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMilestone.sequence_order",
    )
