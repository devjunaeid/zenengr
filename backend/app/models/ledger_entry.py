"""LedgerEntry model (FEAT-018, TODO-178).

Append-only project ledger entry. Entries are immutable; corrections are
recorded as new offsetting entries, never edits/deletes. Per FR-18.1 the
ledger persists charges and manual adjustments only - the payment stream is
derived from the existing Transaction stream at read time (no mirror writes).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import LedgerEntryType, LedgerSourceType


class LedgerEntry(TimestampMixin, Base):
    """Append-only project ledger entry (FEAT-018). Immutable; corrections
    are new offsetting entries, never edits/deletes."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        Index("ix_ledger_entries_project_type", "project_id", "type"),
        Index("ix_ledger_entries_project_date", "project_id", "entry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[LedgerEntryType] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)  # always positive
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_type: Mapped[LedgerSourceType | None] = mapped_column(nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    invoice_ref: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
