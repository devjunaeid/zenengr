---
id: TODO-008
title: Tenant edit, suspend, deactivate API + UI
feature: FEAT-001
story: US-005
status: done
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

- [x] PATCH /api/admin/tenants/{id} updates editable fields.
- [x] POST /api/admin/tenants/{id}/suspend sets status=Suspended.
- [x] POST /api/admin/tenants/{id}/deactivate sets status=Cancelled.
- [x] Suspended tenant users blocked at login (US-005 AC6, linked to TODO-009).
- [x] Status transitions audited (FR-4.13, linked to TODO-042).
- [x] Super Admin UI with confirmation dialogs for destructive actions.

## Notes

Suspended = reversible. Cancelled = data preserved but inaccessible.

Verified in code: PATCH /admin/tenants/{id} (edit), POST /admin/tenants/{id}/suspend, /reactivate, /cancel (app/api/v1/admin.py); audit logged in services/tenants.py; UI lifecycle actions in frontend/src/routes/admin/tenants/[id]/+page.svelte.
