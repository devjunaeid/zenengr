---
id: TODO-015
title: Tenant subscription view/edit in Super Admin panel
feature: FEAT-002
story: US-008
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-012]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-015 — Tenant subscription view/edit in Super Admin panel

## Description

Build Super Admin view/edit panel for tenant subscription details: assigned plan, billing cycle, renewal date, subscription status.

## Acceptance criteria

- [x] Super Admin panel shows tenant subscription status, plan, cycle, renewal date.
- [x] Super Admin can assign/change plan (FR-2.1).
- [x] Super Admin can edit subscription status, billing cycle, renewal date manually (FR-2.3).
- [x] Changes audited (FR-4.13).
- [x] Tenant Admin can view but not edit.

## Notes

MVP uses manual tracking. Automated billing Phase 2.

Verified in code: subscription GET/PATCH at app/api/v1/admin.py (super admin), services/tenants.py subscription logic with audit; UI form in frontend/src/routes/admin/tenants/[id]/+page.svelte (plan/status/cycle/renewal).
