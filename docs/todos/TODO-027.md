---
id: TODO-027
title: Registration flow for invited users
feature: FEAT-004
story: US-012
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-026]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-027 — Registration flow for invited users

## Description

Build registration page for invited admin users. Validate invite token, collect name/password, create user account with pre-assigned role, mark invite accepted.

## Acceptance criteria

- [x] GET /api/auth/invite/{token} validates token and returns email + role.
- [x] POST /api/auth/register creates user account from valid invite.
- [x] Expired token returns 410 Gone (FR-4.9).
- [x] Already-accepted token returns 409 Conflict.
- [x] After registration, user can log into Admin Portal with role permissions (US-012 AC5).
- [x] Invite acceptance tracked in audit trail (audit.log entry for user.registered).

## Notes

