---
id: TODO-147
title: Client settings endpoint (backend)
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-147 - Client settings endpoint (backend)

## Description

Add `GET /client/settings` returning the 4 formatting keys for the client realm: `{currency, timezone, date_format, time_format}` - read-only, no permission internals. Add tests.

## Acceptance criteria

- [x] `GET /client/settings` returns `{currency, timezone, date_format, time_format}` for client realm. (FR-14.1)
- [x] Read-only - no permission internals exposed. (FR-14.1)
- [x] Tests cover happy path and client auth requirement.

## Notes

- Client portal counterpart to staff `GET /tenant/settings`. (FR-14.1)
- Shipped 2026-08-05: `GET /client/settings` (client realm) returns the 4 formatting keys, read-only; tests cover happy path + client auth requirement.
