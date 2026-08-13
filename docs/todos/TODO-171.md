---
id: TODO-171
title: WebSocket connection manager + endpoints
feature: FEAT-017
story: US-059
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-170]
blocks: [TODO-173, TODO-174]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-171 - WebSocket connection manager + endpoints

## Description

ConnectionManager: user_id -> set of websockets; admin + client realms; token auth via query param; send/close. Endpoints /ws/admin + /ws/client. Fan-out on notification create (new notification + unread-count bump). Tests via httpx/starlette test client.

## Acceptance criteria

- [x] ConnectionManager (user_id -> set[websocket]; admin + client realms). (FR-17.4)
- [x] /ws/admin + /ws/client endpoints with token auth via query param. (FR-17.4, AC-5)
- [x] Fan-out on create: pushes notification + unread-count bump to connected sockets. (FR-17.4, AC-5)
- [x] Tests: WS auth (valid/invalid token), connect/disconnect, fan-out per user, realm separation.

## Notes

- Client (frontend) auto-reconnects with backoff (TODO-174); server just accepts/refuses + pushes.
- Shipped: ConnectionManager + /ws/admin + /ws/client with token auth via query param; fan-out pushes notification + unread-count bump; WS tests.
