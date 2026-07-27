---
id: TODO-022
title: Plan default flag configuration
feature: FEAT-003
story: US-010
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-020, TODO-012]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-022 — Plan default flag configuration

## Description

Build UI + API for Super Admin to set default feature flag values per Plan. Overrides persist independently of plan defaults (FR-3.3).

## Acceptance criteria

- [ ] Plan edit page includes Feature Flags section with default on/off per flag.
- [ ] Tenant override persists when plan defaults change (FR-3.3 AC-6).
- [ ] GET /api/admin/plans/{id}/flags returns plan defaults.
- [ ] PUT /api/admin/plans/{id}/flags updates plan defaults.

## Notes

