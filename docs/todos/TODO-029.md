---
id: TODO-029
title: Role edit API + UI
feature: FEAT-004
story: US-013
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-012]
blocks: [TODO-031]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-029 — Role edit API + UI

## Description

Build endpoint + UI for Tenant Admin to change an admin user's role. Role changes take effect on next API request. Last-admin guard enforced.

## Acceptance criteria

- [ ] PATCH /api/tenant/users/{id}/role changes role field.
- [ ] Role change takes effect on next request (no re-login needed) (FR-4.10).
- [ ] UI role selector with confirmation dialog.
- [ ] Last-admin guard prevents removing last Admin role (TODO-031).
- [ ] Change audited (TODO-042).

## Notes

