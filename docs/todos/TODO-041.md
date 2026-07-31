---
id: TODO-041
title: Audit log viewer for Tenant Admin
feature: FEAT-004
story: US-017
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-040]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-041 — Audit log viewer for Tenant Admin

## Description

Build audit log viewer page for Tenant Admin showing recent actions: who, what, when. Filterable by action type and date range.

## Acceptance criteria

- [x] GET /api/tenant/audit-logs returns paginated log entries.
- [x] UI table: timestamp, actor name, action description, entity link.
- [x] Filter by action type and date range.
- [x] Read-only view — no edit or delete.
- [x] Super Admin has equivalent view (all tenants).

## Notes

