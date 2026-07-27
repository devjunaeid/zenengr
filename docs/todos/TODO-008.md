---
id: TODO-008
title: Tenant edit, suspend, deactivate API + UI
feature: FEAT-001
story: US-005
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-005]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-008 — Tenant edit, suspend, deactivate API + UI

## Description

Build endpoints + Super Admin UI for editing tenant profile fields, suspending (reversible), and deactivating (permanent) tenants. Status transitions logged in audit trail.

## Acceptance criteria

- [ ] PATCH /api/admin/tenants/{id} updates editable fields.
- [ ] POST /api/admin/tenants/{id}/suspend sets status=Suspended.
- [ ] POST /api/admin/tenants/{id}/deactivate sets status=Cancelled.
- [ ] Suspended tenant users blocked at login (US-005 AC6, linked to TODO-009).
- [ ] Status transitions audited (FR-4.13, linked to TODO-042).
- [ ] Super Admin UI with confirmation dialogs for destructive actions.

## Notes

Suspended = reversible. Cancelled = data preserved but inaccessible.
