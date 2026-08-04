"""Transaction + PaymentAllocation models (FEAT-009, TODO-089/090/092/093).

A Transaction records a payment against an issued or partially paid invoice.
PaymentAllocation rows break the payment into per-line-item amounts, either
from explicit client input (TODO-094) or computed proportionally.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import PaymentMethod
from app.models.invoice import Invoice


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(nullable=False)
    reference_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoice: Mapped[Invoice] = relationship("Invoice")
    allocations: Mapped[list[PaymentAllocation]] = relationship(
        "PaymentAllocation",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="PaymentAllocation.created_at",
    )


class PaymentAllocation(TimestampMixin, Base):
    __tablename__ = "payment_allocations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("transactions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    line_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("invoice_line_items.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    transaction: Mapped[Transaction] = relationship("Transaction", back_populates="allocations")
