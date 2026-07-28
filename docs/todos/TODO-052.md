---
id: TODO-052
title: Portal access gate for archived clients
feature: FEAT-005
story: US-021
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-051]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-052 — Portal access gate for archived clients

## Description

Add check in Client Portal auth/login: if client's status is Archived, Client User is blocked from accessing the portal.

## Acceptance criteria

- [ ] Client Portal login checks client.status — Archived returns error message.
- [ ] Active Client Portal sessions for archived client revoked on next request.
- [ ] Unarchiving client restores portal access.

## Notes

