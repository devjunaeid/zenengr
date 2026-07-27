---
id: TODO-031
title: Last-admin guard logic
feature: FEAT-004
story: US-013
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-029]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-031 — Last-admin guard logic

## Description

Implement guard preventing deactivation or role-change-away-from-Admin of the tenant's last remaining active Admin user (FR-4.14).

## Acceptance criteria

- [ ] Before deactivating or changing role away from Admin: count active Admin users in tenant.
- [ ] If count <= 1 and target is the target user: block with 422 and message.
- [ ] Guard applies to both deactivate (TODO-030) and role change (TODO-029) endpoints.
- [ ] Super Admin bypasses this guard.

## Notes

