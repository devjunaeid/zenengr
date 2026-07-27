"""Email abstraction layer.

Uses a Protocol-based EmailSender interface.
ConsoleEmailSender logs payload (default for dev).
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

EMAIL_BACKEND_CONSOLE = "console"


@runtime_checkable
class EmailSender(Protocol):
    """Protocol for email sender implementations."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> None: ...


class ConsoleEmailSender:
    """Logs email payload to console. Default for local dev."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        *,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> None:
        logger.info(
            "Email to=%s subject=%s cc=%s bcc=%s body=%s",
            to,
            subject,
            cc or [],
            bcc or [],
            body,
        )


def create_email_sender(backend: str = EMAIL_BACKEND_CONSOLE) -> EmailSender:
    """Factory — returns backend based on config string.

    Currently only 'console' is implemented.
    """
    if backend == EMAIL_BACKEND_CONSOLE:
        return ConsoleEmailSender()
    msg = f"Unknown email backend: {backend}"
    raise ValueError(msg)
