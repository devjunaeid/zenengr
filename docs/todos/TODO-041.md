---
id: TODO-041
title: Audit log viewer for Tenant Admin
feature: FEAT-004
story: US-017
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-040]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-041 — Audit log viewer for Tenant Admin

## Description

Build audit log viewer page for Tenant Admin showing recent actions: who, what, when. Filterable by action type and date range.

## Acceptance criteria

- [ ] GET /api/tenant/audit-logs returns paginated log entries.
- [ ] UI table: timestamp, actor name, action description, entity link.
- [ ] Filter by action type and date range.
- [ ] Read-only view — no edit or delete.
- [ ] Super Admin has equivalent view (all tenants).

## Notes

