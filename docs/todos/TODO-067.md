---
id: TODO-067
title: Assignee picker component
feature: FEAT-007
story: US-026
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-065]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-067 — Assignee picker component

## Description

Build user picker component for milestone assignment. Shows tenant admin users with search.

## Acceptance criteria

- [ ] Assignee picker loads GET /api/tenant/users (active admins only).
- [ ] Search-by-name filtering.
- [ ] Selected user shown as avatar/chip in milestone row.
- [ ] Assignee change calls PATCH endpoint.

## Notes

