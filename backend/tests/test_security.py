"""Tests for password hashing and JWT token service."""

from __future__ import annotations

from datetime import datetime, timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.enums import AdminUserRole


class TestPassword:
    def test_hash_and_verify(self):
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("secret123")
        assert verify_password("wrong", hashed) is False

    def test_different_hash_each_time(self):
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2


class TestJWT:
    def test_roundtrip(self):
        token = create_access_token(
            user_id="u1",
            tenant_id="t1",
            role=AdminUserRole.ADMIN.value,
            realm="admin",
        )
        payload = decode_access_token(token)
        assert payload.sub == "u1"
        assert payload.tenant_id == "t1"
        assert payload.role == AdminUserRole.ADMIN.value
        assert payload.realm == "admin"
        assert isinstance(payload.iat, datetime)
        assert isinstance(payload.exp, datetime)

    def test_expired_token_rejected(self):
        token = create_access_token(
            user_id="u1",
            tenant_id=None,
            role=AdminUserRole.ADMIN.value,
            realm="admin",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(token)

    def test_tampered_token_rejected(self):
        token = create_access_token(
            user_id="u1",
            tenant_id=None,
            role=AdminUserRole.ADMIN.value,
            realm="admin",
        )
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(tampered)

    def test_client_realm_decodes_successfully(self):
        """Client-portal token decodes fine; realm check happens in auth middleware."""
        token = create_access_token(
            user_id="u1",
            tenant_id=None,
            role="client",
            realm="client",
        )
        payload = decode_access_token(token)
        assert payload.realm == "client"

    def test_missing_required_claims_fails(self):
        settings = __import__("app.core.config", fromlist=["get_settings"]).get_settings()
        bad = jwt.encode({"sub": "u1"}, settings.jwt_secret, algorithm="HS256")
        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(bad)

    def test_none_tenant_id(self):
        token = create_access_token(
            user_id="u1",
            tenant_id=None,
            role=AdminUserRole.SUPER_ADMIN.value,
            realm="admin",
        )
        payload = decode_access_token(token)
        assert payload.tenant_id is None
