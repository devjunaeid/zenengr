from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import ClientStatus, ClientType

if TYPE_CHECKING:
    from app.models.client_note import ClientNote
    from app.models.client_user import ClientUser
    from app.models.tenant import Tenant


class Client(TimestampMixin, Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[ClientType] = mapped_column(default=ClientType.COMPANY, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_address: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ClientStatus] = mapped_column(default=ClientStatus.ACTIVE, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="clients")
    client_users: Mapped[list[ClientUser]] = relationship("ClientUser", back_populates="client")
    notes: Mapped[list[ClientNote]] = relationship("ClientNote", back_populates="client")
