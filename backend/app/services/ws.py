"""WebSocket connection manager (FEAT-017, TODO-171).

Tracks connected sockets per recipient key `"<user_type>:<user_id>"`
(admin_user / client_user). Broadcasts are fire-and-forget: a failing
socket (dead connection) is dropped and removed from the set.
"""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._conns: dict[str, set[WebSocket]] = {}

    async def connect(self, key: str, ws: WebSocket) -> None:
        """Register a socket for a recipient key."""
        self._conns.setdefault(key, set()).add(ws)

    def disconnect(self, key: str, ws: WebSocket) -> None:
        """Unregister a socket; drop the key when its last socket leaves."""
        conns = self._conns.get(key)
        if conns is None:
            return
        conns.discard(ws)
        if not conns:
            self._conns.pop(key, None)

    def is_connected(self, key: str) -> bool:
        """True when at least one live socket is registered for the key."""
        return bool(self._conns.get(key))

    async def broadcast_to_keys(self, keys: list[str], payload: dict[str, Any]) -> None:
        """Send payload to every socket registered for the given keys.

        A socket that raises while sending is considered dead and is
        disconnected (removed). Other sockets are unaffected.
        """
        for key in keys:
            conns = self._conns.get(key)
            if not conns:
                continue
            for ws in list(conns):
                try:
                    await ws.send_json(payload)
                except Exception:
                    self.disconnect(key, ws)


manager = ConnectionManager()
