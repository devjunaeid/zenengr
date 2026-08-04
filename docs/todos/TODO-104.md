---
id: TODO-104
title: Visibility filtering in thread queries
feature: FEAT-010
story: US-040
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-103]
blocks: []
created: "2026-07-26"
updated: "2026-08-03"
---

# TODO-104 — Visibility filtering in thread queries

## Description

Server-side filtering: Client Portal requests exclude is_internal=true comments. Internal-only comments never leak to Client Portal.

## Acceptance criteria

- [x] GET /api/client/projects/{id}/comments filters out is_internal=true.
- [x] GET /api/tenant/projects/{id}/comments returns all comments.
- [x] Filtering is server-side enforced (not just UI) (FR-10.3).
- [x] Client User cannot access internal comments via any API path.

## Notes

Server-side filtering: client GET filters is_internal=false; tenant GET returns all. Client project access scoped to user's client_id (404 leak prevention).

