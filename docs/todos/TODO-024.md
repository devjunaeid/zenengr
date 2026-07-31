---
id: TODO-024
title: Tenant feature status read-only view
feature: FEAT-003
story: US-011
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-020]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-024 — Tenant feature status read-only view

## Description

Build page for Tenant Admin showing which features are enabled/disabled for their tenant. Read-only, no toggle.

## Acceptance criteria

- [x] GET /api/tenant/flags returns flag key + enabled status for current tenant.
- [x] UI shows enabled/disabled badges per feature.
- [x] No edit controls for Tenant Admin (FR-3.4).
- [ ] Disabled feature shows optional "request upgrade" prompt (FR-3.4, linked to TODO-025).

## Notes

- AC4 (disabled-flag "request upgrade" prompt) not yet met. Plan page renders read-only pills only; no upgrade CTA wired. Belongs to TODO-025.

