---
id: TODO-046
title: Client list API with rollups
feature: FEAT-005
story: US-019
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043, TODO-095]
blocks: [TODO-047]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-046 — Client list API with rollups

## Description

Extend client list API with summary rollups: active project count, total invoiced, total outstanding balance (FR-5.4). Computed from live invoice/transaction data.

## Acceptance criteria

- [ ] GET /api/tenant/clients returns rollups per client.
- [ ] Rollups: active_projects_count, total_invoiced, total_outstanding.
- [ ] Computed live (not stored) from TODO-095 service.
- [ ] Sortable by rollup values.

## Notes

