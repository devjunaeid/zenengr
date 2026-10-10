"""Payment model (FEAT-027, TODO-221).

Single source of truth for client payments and refunds.
A payment is recorded against a client (and optionally a project).
Its amount can be allocated across one or more invoices via PaymentAllocation.
Unallocated payment amount represents client advance credit.
Supports soft-delete (void) with restore per ADR-004.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import PaymentKind, PaymentMethod

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.client import Client
    from app.models.project import Project
    from app.models.tenant import Tenant
    from app.models.transaction import PaymentAllocation


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_tenant_project_date", "tenant_id", "project_id", "paid_on"),
        Index("ix_payments_tenant_client", "tenant_id", "client_id"),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kind: Mapped[PaymentKind] = mapped_column(
        default=PaymentKind.RECEIPT, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        default=PaymentMethod.BANK_TRANSFER, nullable=False
    )
    paid_on: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    reference_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )

    # Soft-delete / Void with Restore (ADR-004)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant")
    client: Mapped[Client] = relationship("Client")
    project: Mapped[Project | None] = relationship("Project")
    recorded_by: Mapped[AdminUser | None] = relationship(
        "AdminUser", foreign_keys=[recorded_by_id]
    )
    voided_by: Mapped[AdminUser | None] = relationship(
        "AdminUser", foreign_keys=[voided_by_id]
    )
    allocations: Mapped[list[PaymentAllocation]] = relationship(
        "PaymentAllocation",
        back_populates="payment",
        cascade="all, delete-orphan",
    )
