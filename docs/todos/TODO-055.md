---
id: TODO-055
title: Field-level permission enforcement
feature: FEAT-005
story: US-022
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-034, TODO-054]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-055 — Field-level permission enforcement

## Description

Implement server-side field-level permission checks for client profile edits. Client User can edit contact fields only; billing fields staff-only.

## Acceptance criteria

- [ ] Field permission map: contact_fields (editable by Client User + staff), billing_fields (staff only).
- [ ] PATCH endpoint rejects billing field changes from Client User role.
- [ ] Tenant Admin/Manager can edit all fields (FR-5.1).

## Notes

