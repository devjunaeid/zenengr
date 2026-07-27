"""Password hashing and JWT service.

Uses bcrypt directly (no passlib wrapper) for hashing and PyJWT (HS256)
for token creation/verification.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt
from pydantic import BaseModel

from app.core.config import get_settings

# ── Password hashing ──────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt."""
    hashed: bytes = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext against bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT token types ───────────────────────────────────────────────────────


class TokenPayload(BaseModel):
    """Decoded JWT payload for admin realm tokens."""

    sub: str  # user_id (uuid as string)
    tenant_id: str | None = None
    client_id: str | None = None
    role: str
    realm: Literal["admin", "client"]
    iat: datetime
    exp: datetime


# ── JWT token service ─────────────────────────────────────────────────────


def create_access_token(
    *,
    user_id: str,
    tenant_id: str | None,
    role: str,
    realm: Literal["admin", "client"],
    expires_delta: timedelta | None = None,
    client_id: str | None = None,
) -> str:
    """Create signed HS256 JWT access token.

    Default TTL: 24 hours. No refresh token in MVP.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    ttl = expires_delta or timedelta(hours=24)

    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "role": role,
        "realm": realm,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate JWT. Raises on invalid/expired/tampered token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "realm", "exp", "iat"]},
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
    return TokenPayload(**payload)
