---
id: TODO-024
title: Tenant feature status read-only view
feature: FEAT-003
story: US-011
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-020]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-024 — Tenant feature status read-only view

## Description

Build page for Tenant Admin showing which features are enabled/disabled for their tenant. Read-only, no toggle.

## Acceptance criteria

- [ ] GET /api/tenant/flags returns flag key + enabled status for current tenant.
- [ ] UI shows enabled/disabled badges per feature.
- [ ] No edit controls for Tenant Admin (FR-3.4).
- [ ] Disabled feature shows optional "request upgrade" prompt (FR-3.4, linked to TODO-025).

## Notes

