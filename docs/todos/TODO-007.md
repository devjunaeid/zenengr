---
id: TODO-007
title: Tenant list view
feature: FEAT-001
story: US-005
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-007 — Tenant list view

## Description

Build Super Admin tenant list page showing all tenants with status, plan, key metadata. Include search/filter by status.

## Acceptance criteria

- [x] GET /api/admin/tenants returns paginated list with tenant data.
- [x] Super Admin UI table: business name, slug, status badge, plan name, created date.
- [x] Filter by status (Trial/Active/Suspended/Cancelled).
- [x] Sortable columns (name, created date).

## Notes

Sortable Name/Created columns on admin tenant list (URL sort param, business_name/created_at + - prefix, arrow indicator).

