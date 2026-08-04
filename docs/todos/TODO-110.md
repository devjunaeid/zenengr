---
id: TODO-110
title: Email change with re-verification
feature: FEAT-011
story: US-042
status: done
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

- [x] POST /api/auth/change-email initiates email change: stores pending email + sends verification.
- [x] Old email remains active for login until verified (FR-11.5).
- [x] Verification link in new email: confirm change.
- [x] After verification: update user email, log in activity history (TODO-119).
- [x] Failed/expired verification: pending change discarded.

## Notes

pending_email columns + EmailVerificationToken model + migration b2c3d4e5f6a7. PATCH profile with email sets pending_email + sends verification link (portal /verify-email?token=); old email active until verified. Public verify endpoints both realms: 404 unknown / 410 expired / 409 already-used or duplicate email. Activity email.changed with old/new values.
