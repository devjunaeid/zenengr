---
id: TODO-104
title: Visibility filtering in thread queries
feature: FEAT-010
story: US-040
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-103]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-104 — Visibility filtering in thread queries

## Description

Server-side filtering: Client Portal requests exclude is_internal=true comments. Internal-only comments never leak to Client Portal.

## Acceptance criteria

- [ ] GET /api/client/projects/{id}/comments filters out is_internal=true.
- [ ] GET /api/tenant/projects/{id}/comments returns all comments.
- [ ] Filtering is server-side enforced (not just UI) (FR-10.3).
- [ ] Client User cannot access internal comments via any API path.

## Notes

