---
id: TODO-035
title: Endpoint authorization decorators/middleware
feature: FEAT-004
story: US-015
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-034]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-035 — Endpoint authorization decorators/middleware

## Description

Apply role-based permission checks at every protected FastAPI endpoint. Server-side enforcement — UI hiding is secondary defense.

## Acceptance criteria

- [ ] FastAPI dependency: requires_permission(action, resource) using TODO-034 service.
- [ ] Every protected endpoint includes permission check.
- [ ] Unauthorized returns 403.
- [ ] Role changes effective on next request (no stale JWT claims — check DB each request).

## Notes

