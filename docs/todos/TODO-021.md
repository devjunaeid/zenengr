---
id: TODO-021
title: Super Admin flag management UI
feature: FEAT-003
story: US-010
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-020]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-021 — Super Admin flag management UI

## Description

Build Super Admin UI to view/edit per-tenant feature flags. Toggle on/off with current state clearly shown.

## Acceptance criteria

- [ ] UI shows all flag keys for tenant with on/off toggle.
- [ ] Toggle calls PATCH /api/admin/tenants/{id}/flags/{key}.
- [ ] Flag state saved as tenant override (TODO-020).
- [ ] Changes take effect on next request without restart (FR-3.5).

## Notes

