---
id: TODO-054
title: Client Portal client profile edit (limited fields)
feature: FEAT-005
story: US-022
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043, TODO-038]
blocks: [TODO-055]
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-054 — Client Portal client profile edit (limited fields)

## Description

Build Client Portal page for Client User to edit own client's contact details (phone, email). Billing-sensitive fields (tax ID, billing address) read-only.

## Acceptance criteria

- [ ] Client Portal shows editable fields: phone, email.
- [ ] Billing-sensitive fields: tax ID, billing address displayed but read-only (FR-5.9).
- [ ] PATCH /api/client/profile updates editable fields.
- [ ] Server enforces field-level permissions (TODO-055).

## Notes

