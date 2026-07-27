---
id: TODO-033
title: Reset email with distinct template
feature: FEAT-004
story: US-014
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-032]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-033 — Reset email with distinct template

## Description

Create email template for admin-triggered password reset, distinct from self-service forgot-password flow (FEAT-011).

## Acceptance criteria

- [ ] Email template: "Your admin has initiated a password reset for your account."
- [ ] Includes reset link with secure token.
- [ ] Template uses tenant branding (TODO-011).
- [ ] Link expires after defined period.

## Notes

