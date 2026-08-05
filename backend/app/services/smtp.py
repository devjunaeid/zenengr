"""Per-tenant SMTP sending (FEAT-013).

Provides:
- Fernet encryption/decryption of SMTP passwords (key derived from
  the JWT secret via sha256 -> urlsafe base64).
- SmtpEmailSender: async sender over aiosmtplib supporting plain,
  STARTTLS, and implicit SSL connections.
- get_sender_for_tenant: factory that resolves the tenant's stored
  config into an EmailSender, falling back to ConsoleEmailSender when
  SMTP is not enabled/configured.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from email.message import EmailMessage

import aiosmtplib
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import ActorType, SmtpSecurityMode
from app.models.tenant_smtp_config import TenantSmtpConfig
from app.services.audit import log as audit_log
from app.services.email import ConsoleEmailSender, EmailSender


def _fernet() -> Fernet:
    """Build a Fernet cipher from the JWT secret (sha256 -> urlsafe base64)."""
    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().jwt_secret.encode()).digest())
    return Fernet(key)


def encrypt_password(plain: str) -> str:
    """Encrypt a plaintext SMTP password to a Fernet token (str)."""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted SMTP password back to plaintext."""
    return _fernet().decrypt(ciphertext.encode()).decode()


class SmtpEmailSender:
    """Sends email through an SMTP server.

    Supports plain (mode NONE), STARTTLS, and implicit SSL connections.
    Raises on failure; callers decide how to surface the error.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int | None,
        username: str | None,
        password: str | None,
        mode: SmtpSecurityMode,
        from_email: str,
        from_name: str | None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.mode = mode
        self.from_email = from_email
        self.from_name = from_name

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> None:
        """Send a text/plain email through the configured SMTP server."""
        msg = EmailMessage()
        if self.from_name:
            msg["From"] = f"{self.from_name} <{self.from_email}>"
        else:
            msg["From"] = self.from_email
        msg["To"] = to
        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)
        msg["Subject"] = subject
        msg.set_content(body)

        client = aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=self.mode == SmtpSecurityMode.SSL,
            start_tls=self.mode == SmtpSecurityMode.STARTTLS,
        )
        try:
            await client.connect()
            if self.username:
                await client.login(self.username, self.password or "")
            await client.send_message(msg)
        finally:
            if client.is_connected:
                await client.quit()


async def get_sender_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> EmailSender:
    """Resolve the tenant's SMTP config into an EmailSender.

    Falls back to ConsoleEmailSender when no config row exists, SMTP is
    disabled, or host/from_email are missing.
    """
    stmt = select(TenantSmtpConfig).where(TenantSmtpConfig.tenant_id == tenant_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()

    if config is None or not config.enabled or not config.host or not config.from_email:
        return ConsoleEmailSender()

    password = decrypt_password(config.password_ciphertext) if config.password_ciphertext else None
    return SmtpEmailSender(
        host=config.host,
        port=config.port,
        username=config.username,
        password=password,
        mode=config.mode,
        from_email=config.from_email,
        from_name=config.from_name,
    )


async def send_tenant_email(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    to: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> None:
    """Send email via tenant SMTP when configured; never raises.

    - resolves sender via get_sender_for_tenant (console fallback when
      disabled or when tenant_id is None)
    - if sender is SmtpEmailSender and send raises: audit 'email.send_failed'
      (details host + error string, entity_type smtp, entity_id tenant_id),
      then fall back to ConsoleEmailSender.send_email (dev log) so the action
      completes; commit after the audit row.
    - console sender path: plain send (no audit).
    """
    if tenant_id is None:
        sender: EmailSender = ConsoleEmailSender()
    else:
        sender = await get_sender_for_tenant(session, tenant_id=tenant_id)

    if isinstance(sender, SmtpEmailSender):
        try:
            await sender.send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        except Exception as exc:
            await audit_log(
                session,
                tenant_id=tenant_id,
                actor_id=None,
                actor_type=ActorType.SYSTEM,
                action="email.send_failed",
                entity_type="smtp",
                entity_id=str(tenant_id),
                details={"host": sender.host, "error": str(exc)},
            )
            await session.commit()
            console = ConsoleEmailSender()
            await console.send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return

    await sender.send_email(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
