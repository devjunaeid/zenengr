"""TenantSmtpConfig model (FEAT-013, TODO-138).

One row per tenant holding outbound SMTP settings: host/port/credentials,
security mode (none/starttls/ssl), sender identity, and enabled flag.

The password is stored as a Fernet-encrypted ciphertext in
password_ciphertext; it is never returned by the API.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin
from app.models.enums import SmtpSecurityMode


class TenantSmtpConfig(TimestampMixin, Base):
    __tablename__ = "tenant_smtp_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id"), unique=True, nullable=False
    )
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_ciphertext: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,  # Fernet-encrypted
    )
    from_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mode: Mapped[SmtpSecurityMode] = mapped_column(
        default=SmtpSecurityMode.STARTTLS, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
