---
id: TODO-067
title: Assignee picker component
feature: FEAT-007
story: US-026
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-065]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-067 — Assignee picker component

## Description

Build user picker component for milestone assignment. Shows tenant admin users with search.

## Acceptance criteria

- [x] Assignee picker loads GET /api/tenant/users (active admins only).
- [x] Search-by-name filtering.
- [x] Selected user shown as avatar/chip in milestone row.
- [x] Assignee change calls PATCH endpoint.

## Notes

