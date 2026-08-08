---
id: TODO-172
title: Notifications REST API (staff + client)
feature: FEAT-017
story: US-059
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-169]
blocks: [TODO-174]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-172 - Notifications REST API (staff + client)

## Description

Staff: GET /tenant/notifications (paginated, tenant + user scoped), GET unread-count, POST /{id}/read, POST read-all. Client equivalents: /client/notifications. Tests.

## Acceptance criteria

- [ ] GET /tenant/notifications paginated, tenant + user scoped. (FR-17.5, AC-1)
- [ ] GET unread-count; POST /{id}/read; POST read-all. (FR-17.5, AC-1)
- [ ] Client equivalents /client/notifications (list, unread-count, mark-read, mark-all). (FR-17.5, AC-1)
- [ ] Tests: scoping (own notifications only), pagination, mark read/all, client realm isolation.

## Notes

- Read state per user; no cross-user or cross-tenant reads.
