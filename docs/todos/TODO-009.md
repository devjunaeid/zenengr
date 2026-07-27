---
id: TODO-009
title: Login gate for suspended/deactivated tenants
feature: FEAT-001
story: US-005
status: in_progress
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

- [ ] Login rejects users from Suspended tenants with descriptive message.
- [ ] Login rejects users from Cancelled tenants with descriptive message.
- [ ] Active/Trial tenants login normally.
- [ ] Check applies to both Admin Portal and Client Portal auth realms.

## Notes

