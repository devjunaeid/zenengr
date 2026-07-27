---
id: TODO-018
title: Settings UI for Tenant Admin (editable + view-only)
feature: FEAT-002
story: US-009
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-017]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-018 — Settings UI for Tenant Admin (editable + view-only)

## Description

Build settings page for Tenant Admin: editable fields have save controls, view-only fields display values with lock icon. Server enforces permissions.

## Acceptance criteria

- [ ] Settings page renders all settings with correct editable/read-only state per permission matrix.
- [ ] Editable fields submit PATCH /api/tenant/settings.
- [ ] View-only fields show value with lock indicator.
- [ ] Server rejects edits on SuperAdminOnly settings.

## Notes

