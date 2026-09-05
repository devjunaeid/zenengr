"""Project model (FEAT-007).

A Project bundles one or more services for a specific client. Each attached
service becomes a ProjectService (join entity) that instantiates its
MilestoneStepTemplate as ProjectMilestone rows.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import DiscountType, ProjectMemberRole, ProjectStatus

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
    status: Mapped[ProjectStatus] = mapped_column(default=ProjectStatus.DRAFT, nullable=False)
    # Opt-in AUTO-INVOICE: when True, the project keeps an open draft invoice
    # that is auto-created / auto-appended as services are attached.
    auto_invoice: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id"), nullable=True
    )
    # Single active discount per project (FEAT-018, FR-18.3): replace-on-change,
    # audited via discount_updated_at/discount_updated_by, never on client timeline.
    discount_type: Mapped[DiscountType | None] = mapped_column(nullable=True)
    discount_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    discount_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    discount_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="projects")
    client: Mapped[Client] = relationship("Client", back_populates="projects")
    owner: Mapped[AdminUser | None] = relationship("AdminUser", foreign_keys=[owner_id])
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
    members: Mapped[list[ProjectMember]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMember(TimestampMixin, Base):
    __tablename__ = "project_members"
    __table_args__ = (
        Index("uq_project_members_project_user", "project_id", "user_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("admin_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[ProjectMemberRole] = mapped_column(
        Enum(
            ProjectMemberRole,
            native_enum=False,
            values_callable=lambda obj: [e.value for e in obj],
            length=32,
        ),
        default=ProjectMemberRole.CONTRIBUTOR,
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), index=True, nullable=False
    )

    project: Mapped[Project] = relationship("Project", back_populates="members")
    user: Mapped[AdminUser] = relationship("AdminUser")

