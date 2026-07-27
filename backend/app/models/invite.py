from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import InviteRole

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Invite(TimestampMixin, Base):
    """User invitation record.

    token stores a SHA-256 hash of the raw invite token, not the raw value.
    Service layer hashes before insert and hashes when looking up.
    """

    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[InviteRole] = mapped_column(nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("admin_users.id"), nullable=False
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="invites")

    __table_args__ = (Index("ix_invites_token", "token", unique=True),)
