---
id: TODO-114
title: Forgot-password flow
feature: FEAT-011
story: US-043
status: proposed
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

- [ ] POST /api/auth/forgot-password sends reset link to registered email.
- [ ] Reset link page: enter new password + confirm.
- [ ] Link expires after defined period (e.g., 1 hour) (FR-11.2).
- [ ] Expired link returns 410 Gone.
- [ ] Works for both Admin Portal and Client Portal users.

## Notes

