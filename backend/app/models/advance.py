"""Advance model (FEAT-015, TODO-154/155).

An Advance is created when a payment exceeds the remaining balance of an
invoice. The excess is held as an advance balance scoped to a client (or
unassigned when the overpaid invoice was a GENERAL invoice with no project).
Advances can be manually applied to other issued/partially paid invoices of
the same scope via apply_advance.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class Advance(TimestampMixin, Base):
    __tablename__ = "advances"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), index=True, nullable=False
    )
    # None = unassigned (general-invoice advance)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("clients.id"), index=True, nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("invoices.id"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_by_type: Mapped[str] = mapped_column(String(20), nullable=False)
