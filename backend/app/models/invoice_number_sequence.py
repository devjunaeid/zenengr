"""Per-tenant invoice number sequence (FEAT-008, TODO-079).

Single row per tenant, holding the last issued number and the format
template used at issue time. Incremented under a row lock
(FOR UPDATE) to guarantee gapless, race-free invoice numbers.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class InvoiceNumberSequence(TimestampMixin, Base):
    __tablename__ = "invoice_number_sequences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    format_template: Mapped[str] = mapped_column(String(255), nullable=False)
