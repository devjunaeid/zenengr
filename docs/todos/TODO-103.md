---
id: TODO-103
title: Internal/shared comment flag on post
feature: FEAT-010
story: US-040
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-100]
blocks: [TODO-104, TODO-105]
created: "2026-07-26"
updated: "2026-08-03"
---

# TODO-103 — Internal/shared comment flag on post

## Description

Add toggle on comment form for tenant staff: "Internal only" checkbox. Client Users cannot see the toggle (all their comments are shared).

## Acceptance criteria

- [x] Tenant staff comment form has "Internal only" toggle (FR-10.3).
- [x] When toggled: is_internal=true on comment create.
- [x] Client User comment form does NOT show the toggle (all client comments are shared).
- [x] Default is shared (is_internal=false).

## Notes

is_internal flag on tenant comment create (default false). Client portal comments forced shared server-side (body flag ignored).

