---
id: TODO-010
title: Tenant profile self-service page
feature: FEAT-001
story: US-006
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-011]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-010 — Tenant profile self-service page

## Description

Build Tenant Admin page to view/edit own tenant profile (business name, contact info, branding). Super Admin can also edit these fields from SA panel. All edits audited.

## Acceptance criteria

- [ ] GET /api/tenant/profile returns current tenant data for logged-in Tenant Admin.
- [ ] PATCH /api/tenant/profile updates editable fields.
- [ ] Tenant Admin CANNOT change subscription tier or platform settings (US-006 AC3).
- [ ] Super Admin can edit same fields via /api/admin/tenants/{id}.
- [ ] Edits logged in audit trail (linked to TODO-042).

## Notes

