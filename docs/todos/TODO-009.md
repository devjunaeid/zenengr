---
id: TODO-009
title: Login gate for suspended/deactivated tenants
feature: FEAT-001
story: US-005
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-009 — Login gate for suspended/deactivated tenants

## Description

Add tenant status check in auth middleware. Users from Suspended or Cancelled tenants receive appropriate error on login attempt.

## Acceptance criteria

- [x] Login rejects users from Suspended tenants with descriptive message.
- [x] Login rejects users from Cancelled tenants with descriptive message.
- [x] Active/Trial tenants login normally.
- [x] Check applies to both Admin Portal and Client Portal auth realms.

## Notes

Tenant status gate implemented in both auth realms (app/services/auth.py, app/services/client_auth.py) and on every authed request (app/core/dependencies.py). Suspended/Cancelled tenants get 403 with descriptive message; Trial/Active log in normally.

