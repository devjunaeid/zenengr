---
id: TODO-034
title: Role-based permission service
feature: FEAT-004
story: US-015
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-035, TODO-036, TODO-055]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-034 — Role-based permission service

## Description

Build permission service implementing FR-4.2 matrix: Admin full access, Manager manages clients/services/projects/invoices/payments but not admin users or tenant settings, Employee views assigned projects, updates milestones, cannot create invoices or payments.

## Acceptance criteria

- [ ] Permission matrix data-driven (config or DB table) per FR-4.2.
- [ ] Service method: has_permission(user, action, resource) -> bool.
- [ ] Actions defined per resource: create, read, update, delete.
- [ ] Super Admin is separate system-level role, not part of tenant matrix (US-015 Notes).
- [ ] All three roles can edit own profile/password (FR-4.2).
- [ ] Role changes take effect on next request (FR-4.10, linked to TODO-029).

## Notes

