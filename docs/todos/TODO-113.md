---
id: TODO-113
title: Password change API
feature: FEAT-011
story: US-043
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-115]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-113 — Password change API

## Description

Build password change endpoint with current-password confirmation. Incorrect current password rejects change (FR-11.2).

## Acceptance criteria

- [ ] POST /api/auth/change-password with current_password + new_password.
- [ ] Validates current_password before changing.
- [ ] Incorrect current_password returns 403.
- [ ] Password change logged in activity history (TODO-119).
- [ ] Password policy enforced (TODO-115).

## Notes

