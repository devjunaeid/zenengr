"""WebSocket notification endpoints (FEAT-017, TODO-171).

Paths: /api/v1/ws/admin and /api/v1/ws/client. Auth via `token` query
param (same JWT as the REST API); the token's realm must match the
endpoint. Rejects with close code 1008 (policy violation) otherwise.
Registered on a plain router so the api_router prefix yields the final
paths above.

The handler accepts, registers the socket with the ConnectionManager and
then just drains inbound frames to keep the connection alive. Push happens
server-side from app/services/notifications.py (notify_users).
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.services.ws import manager

router = APIRouter()

_REALM_USER_TYPES = {"admin": "admin_user", "client": "client_user"}
_CLOSE_POLICY_VIOLATION = 1008


@router.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket) -> None:
    await _handle_connection(websocket, expected_realm="admin")


@router.websocket("/ws/client")
async def ws_client(websocket: WebSocket) -> None:
    await _handle_connection(websocket, expected_realm="client")


async def _handle_connection(websocket: WebSocket, *, expected_realm: str) -> None:
    token = websocket.query_params.get("token", "")
    try:
        payload = decode_access_token(token)
    except ValueError:
        await websocket.close(code=_CLOSE_POLICY_VIOLATION)
        return
    if payload.realm != expected_realm:
        await websocket.close(code=_CLOSE_POLICY_VIOLATION)
        return

    key = f"{_REALM_USER_TYPES[expected_realm]}:{payload.sub}"
    await websocket.accept()
    await manager.connect(key, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(key, websocket)
