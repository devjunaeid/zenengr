"""PurchaseEntry + PurchaseEntryItem models.

A PurchaseEntry records project-level purchase costs entered by a tenant user.
It is a standalone module with no connection to the Invoice system.

Each entry has a header (title, notes, entry_date) linked to a tenant + project,
and one or more PurchaseEntryItem rows (description, quantity, rate, total).
The server always stores `total = quantity * rate` per item and `grand_total`
(sum of all item totals) on the header for fast reads.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.project import Project


class PurchaseEntry(TimestampMixin, Base):
    """Header record for a purchase entry against a project."""

    __tablename__ = "purchase_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped[Project] = relationship("Project")
    created_by: Mapped[AdminUser | None] = relationship("AdminUser")
    items: Mapped[list[PurchaseEntryItem]] = relationship(
        "PurchaseEntryItem",
        back_populates="purchase_entry",
        cascade="all, delete-orphan",
        order_by="PurchaseEntryItem.created_at",
    )


class PurchaseEntryItem(TimestampMixin, Base):
    """A single line item within a PurchaseEntry."""

    __tablename__ = "purchase_entry_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purchase_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("purchase_entries.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    item_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("1"), nullable=False
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    purchase_entry: Mapped[PurchaseEntry] = relationship(
        "PurchaseEntry", back_populates="items"
    )
