---
id: TODO-028
title: Invite expiry enforcement
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

# TODO-028 — Invite expiry enforcement

## Description

Implement invite expiry check on registration attempt. Expired invite cannot be used to register. Background cleanup for expired invites.

## Acceptance criteria

- [x] Invite validation checks expires_at against current time.
- [x] Expired invite returns 410 Gone on registration attempt.
- [x] Resend invite creates new token and extends expiry.
- [ ] Optional: background job to cleanup or mark expired invites (deferred).

## Notes

