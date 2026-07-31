from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import TenantStatus

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.audit_log import AuditLog
    from app.models.client import Client
    from app.models.client_user import ClientUser
    from app.models.invite import Invite
    from app.models.plan import Plan
    from app.models.project import Project
    from app.models.service import Service
    from app.models.tenant_feature_flag import TenantFeatureFlag
    from app.models.tenant_setting import TenantSetting
    from app.models.tenant_subscription import TenantSubscription


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[TenantStatus] = mapped_column(default=TenantStatus.TRIAL, nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("plans.id"), nullable=False)
    contact_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    branding: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # relationships
    plan: Mapped[Plan] = relationship("Plan", back_populates="tenants")
    subscription: Mapped[TenantSubscription | None] = relationship(
        "TenantSubscription", back_populates="tenant", uselist=False
    )
    settings: Mapped[list[TenantSetting]] = relationship("TenantSetting", back_populates="tenant")
    feature_flags: Mapped[list[TenantFeatureFlag]] = relationship(
        "TenantFeatureFlag", back_populates="tenant"
    )
    admin_users: Mapped[list[AdminUser]] = relationship("AdminUser", back_populates="tenant")
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="tenant")
    invites: Mapped[list[Invite]] = relationship("Invite", back_populates="tenant")
    clients: Mapped[list[Client]] = relationship("Client", back_populates="tenant")
    client_users: Mapped[list[ClientUser]] = relationship("ClientUser", back_populates="tenant")
    services: Mapped[list[Service]] = relationship("Service", back_populates="tenant")
    projects: Mapped[list[Project]] = relationship("Project", back_populates="tenant")
