---
id: TODO-037
title: Client User invite flow
feature: FEAT-004
story: US-016
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-026]
blocks: [TODO-038, TODO-039]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-037 — Client User invite flow

## Description

Extend invite system for Client Users. Tenant Admin/Manager invites client's employee via email, scoped to a specific Client. Client User registers and logs into separate Client Portal.

## Acceptance criteria

- [x] POST /api/tenant/client-invites creates invite for specific client_id.
- [x] Client User registration creates user scoped to that client.
- [x] Invite link directs to Client Portal registration (`client_portal_base_url` setting).
- [x] Client User sees only their own Client's data (FR-4.6, FR-4.8).
- [x] Invite expiry enforced (reuse TODO-028 logic).

## Notes

