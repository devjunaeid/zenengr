---
id: TODO-039
title: Client User deactivation
feature: FEAT-004
story: US-016
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-037]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-039 — Client User deactivation

## Description

Implement Client User deactivation. Tenant Admin/Manager deactivates a Client User's portal access. Deactivated user cannot log into Client Portal.

## Acceptance criteria

- [ ] POST /api/tenant/client-users/{id}/deactivate sets is_active=false.
- [ ] Deactivated Client User blocked at login.
- [ ] Active Client Users unaffected.
- [ ] Action audited (TODO-042).

## Notes

