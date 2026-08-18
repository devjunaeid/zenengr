"""Invoice + InvoiceLineItem models (FEAT-008, TODO-075; FEAT-015, TODO-152).

An Invoice is tenant-scoped and optionally linked to a Project. A NULL
project_id marks a GENERAL (internal) invoice with no client link; such
invoices only carry custom line items. An Invoice carries money snapshots
(subtotal/tax_total/total) plus a snapshot of the line items it was issued
against. invoice_number is assigned only at issue time via the per-tenant
InvoiceNumberSequence.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import InvoiceStatus

if TYPE_CHECKING:
    from app.models.project import Project


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            name="uq_invoices_tenant_invoice_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id"), index=True, nullable=True
    )
    invoice_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.DRAFT, nullable=False)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    project: Mapped[Project | None] = relationship("Project")
    line_items: Mapped[list[InvoiceLineItem]] = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.created_at",
    )


class InvoiceLineItem(TimestampMixin, Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("services.id"), nullable=True
    )
    project_service_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("project_services.id"), nullable=True
    )

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="line_items")
