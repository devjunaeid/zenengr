---
id: TODO-110
title: Email change with re-verification
feature: FEAT-011
story: US-042
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-109]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-110 — Email change with re-verification

## Description

Implement email change flow: request change -> send verification to new email -> old email active until new verified (FR-11.5).

## Acceptance criteria

- [ ] POST /api/auth/change-email initiates email change: stores pending email + sends verification.
- [ ] Old email remains active for login until verified (FR-11.5).
- [ ] Verification link in new email: confirm change.
- [ ] After verification: update user email, log in activity history (TODO-119).
- [ ] Failed/expired verification: pending change discarded.

## Notes

