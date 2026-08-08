"""WebSocket endpoints + connection manager tests (FEAT-017, TODO-171).

WebSocket handshakes only work through starlette's TestClient (httpx
ASGITransport has no WS support), so endpoint tests are plain sync tests.
The manager is exercised in-process with minimal stub sockets.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.main import create_app
from app.services.ws import manager


def _admin_token() -> str:
    return create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        role="admin",
        realm="admin",
    )


def _client_token() -> str:
    return create_access_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        role="client_user",
        realm="client",
        client_id=str(uuid.uuid4()),
    )


class _StubWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed_codes: list[int] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000) -> None:
        self.closed_codes.append(code)


class _FailingWS(_StubWS):
    async def send_json(self, payload: dict) -> None:
        raise RuntimeError("socket dead")


# ═══════════════════════════════════════════════════════════════════════════
# Connection manager (in-process, stub sockets)
# ═══════════════════════════════════════════════════════════════════════════


class TestConnectionManager:
    @pytest.mark.anyio
    async def test_connect_disconnect_is_connected(self):
        key = f"test-key-{uuid.uuid4()}"
        ws = _StubWS()
        assert not manager.is_connected(key)
        await manager.connect(key, ws)  # type: ignore[arg-type]
        assert manager.is_connected(key)
        manager.disconnect(key, ws)  # type: ignore[arg-type]
        assert not manager.is_connected(key)

    @pytest.mark.anyio
    async def test_disconnect_drops_key_when_last_socket_leaves(self):
        key = f"test-key-{uuid.uuid4()}"
        ws1 = _StubWS()
        ws2 = _StubWS()
        await manager.connect(key, ws1)  # type: ignore[arg-type]
        await manager.connect(key, ws2)  # type: ignore[arg-type]
        manager.disconnect(key, ws1)  # type: ignore[arg-type]
        assert manager.is_connected(key)
        manager.disconnect(key, ws2)  # type: ignore[arg-type]
        assert not manager.is_connected(key)

    @pytest.mark.anyio
    async def test_broadcast_to_keys_sends_payload(self):
        key = f"test-key-{uuid.uuid4()}"
        ws1 = _StubWS()
        ws2 = _StubWS()
        await manager.connect(key, ws1)  # type: ignore[arg-type]
        await manager.connect(key, ws2)  # type: ignore[arg-type]
        try:
            payload = {"id": "1", "title": "hello"}
            await manager.broadcast_to_keys([key], payload)
            assert ws1.sent == [payload]
            assert ws2.sent == [payload]
        finally:
            manager.disconnect(key, ws1)  # type: ignore[arg-type]
            manager.disconnect(key, ws2)  # type: ignore[arg-type]

    @pytest.mark.anyio
    async def test_broadcast_drops_dead_socket_keeps_live_ones(self):
        key = f"test-key-{uuid.uuid4()}"
        dead = _FailingWS()
        ok = _StubWS()
        await manager.connect(key, dead)  # type: ignore[arg-type]
        await manager.connect(key, ok)  # type: ignore[arg-type]
        try:
            payload = {"id": "2"}
            # First broadcast: dead socket raises and is removed; ok receives it.
            await manager.broadcast_to_keys([key], payload)
            assert ok.sent == [payload]
            # Second broadcast: only the live socket is left.
            await manager.broadcast_to_keys([key], payload)
            assert ok.sent == [payload, payload]
        finally:
            manager.disconnect(key, ok)  # type: ignore[arg-type]

    @pytest.mark.anyio
    async def test_broadcast_unknown_key_is_noop(self):
        await manager.broadcast_to_keys([f"test-key-{uuid.uuid4()}"], {"id": "3"})


# ═══════════════════════════════════════════════════════════════════════════
# Endpoint auth (TestClient, real token decode, no DB needed)
# ═══════════════════════════════════════════════════════════════════════════


class TestWsEndpoints:
    def test_no_token_closes_1008(self):
        client = TestClient(create_app())
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect("/api/v1/ws/admin"),
        ):
            pass
        assert exc.value.code == 1008

    def test_bad_token_closes_1008(self):
        client = TestClient(create_app())
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect("/api/v1/ws/admin?token=not-a-jwt"),
        ):
            pass
        assert exc.value.code == 1008

    def test_wrong_realm_closes_1008(self):
        client = TestClient(create_app())
        token = _client_token()
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(f"/api/v1/ws/admin?token={token}"),
        ):
            pass
        assert exc.value.code == 1008

    def test_admin_token_connects_and_stays_open(self):
        client = TestClient(create_app())
        token = _admin_token()
        with client.websocket_connect(f"/api/v1/ws/admin?token={token}") as ws:
            ws.send_text("ping")
            ws.send_text("ping again")
        # No exception = accepted, drained frames, closed cleanly.

    def test_client_token_connects_and_stays_open(self):
        client = TestClient(create_app())
        token = _client_token()
        with client.websocket_connect(f"/api/v1/ws/client?token={token}") as ws:
            ws.send_text("ping")
