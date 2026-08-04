---
id: TODO-005
title: Super Admin tenant creation API + UI
feature: FEAT-001
story: US-004
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-008]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-005 — Super Admin tenant creation API + UI

## Description

Build tenant creation endpoint (POST /api/admin/tenants) + Super Admin UI form. Create tenant with business name, slug, initial status (Trial), plan selection. Auto-create Tenant Admin user during provisioning.

## Acceptance criteria

- [x] POST /api/admin/tenants creates tenant + creates Tenant Admin user.
- [x] Slug validated for uniqueness before creation (US-004 AC2).
- [x] Tenant created with status=Trial by default (US-004 AC4).
- [x] Plan assigned at creation (US-004 AC5).
- [x] Super Admin UI form for tenant creation with slug preview.
- [x] Tenant isolation enforced from creation (US-004 AC7).

## Notes

Verified in code: POST /api/v1/admin/tenants (app/api/v1/admin.py), create_tenant service with slug validation/availability + TRIAL default + temp password (app/services/tenants.py); UI at frontend/src/routes/admin/tenants/new/+page.svelte with slug preview/availability.

