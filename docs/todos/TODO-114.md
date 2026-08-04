---
id: TODO-114
title: Forgot-password flow
feature: FEAT-011
story: US-043
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-114 — Forgot-password flow

## Description

Build forgot-password flow: request reset link via email -> click link -> enter new password. Reset link expires after defined period.

## Acceptance criteria

- [x] POST /api/auth/forgot-password sends reset link to registered email.
- [x] Reset link page: enter new password + confirm.
- [x] Link expires after defined period (e.g., 1 hour) (FR-11.2).
- [x] Expired link returns 410 Gone.
- [x] Works for both Admin Portal and Client Portal users.

## Notes

Admin: POST /api/v1/auth/forgot-password (public, no-leak) reuses PasswordResetToken + existing public consume. Client: ClientPasswordResetToken model + POST /client/auth/forgot-password + POST /client/auth/reset-password (404/410/409 semantics). Expiry = password_reset_ttl_hours. Activity + audit logged.

