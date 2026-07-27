---
id: TODO-038
title: Client Portal authentication realm
feature: FEAT-004
story: US-016
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-037]
blocks: [TODO-054, TODO-074, TODO-087, TODO-098, TODO-112]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-038 — Client Portal authentication realm

## Description

Set up separate Client Portal auth realm: login endpoint, JWT session scoped to client user with client_id and tenant_id claims. Separate login page.

## Acceptance criteria

- [ ] Client Portal login page distinct from Admin Portal.
- [ ] POST /api/client/auth/login returns JWT scoped to client user.
- [ ] JWT includes: user_id, client_id, tenant_id, role=client_user.
- [ ] Auth middleware checks tenant status (active/trial) and client archive status.
- [ ] Client User cannot access Admin Portal endpoints.

## Notes

