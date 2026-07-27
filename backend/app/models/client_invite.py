from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.client import Client
    from app.models.tenant import Tenant


class ClientInvite(Base):
    """Client user invitation record.

    Stores SHA-256 hash of raw invite token, never the raw value.
    """

    __tablename__ = "client_invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tenants.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("clients.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("admin_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    tenant: Mapped[Tenant] = relationship("Tenant")
    client: Mapped[Client] = relationship("Client")
    inviter: Mapped[AdminUser] = relationship("AdminUser")

    __table_args__ = (
        Index("ix_client_invites_token_hash", "token_hash", unique=True),
        Index("ix_client_invites_client_email", "client_id", "email"),
    )
