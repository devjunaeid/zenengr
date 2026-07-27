---
id: TODO-026
title: Invite model + email service
feature: FEAT-004
story: US-012
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-027, TODO-028, TODO-037]
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-026 — Invite model + email service

## Description

Create Invite model (email, role, token, expires_at, tenant_id) + email sending service. Tenant Admin invites admin user by email with role pre-assignment.

## Acceptance criteria

- [x] Invite model with: email, role (Admin/Manager/Employee), token hash, expires_at, tenant_id, accepted_at.
- [x] POST /api/tenant/invites creates invite record and sends email with registration link.
- [x] Email service abstraction (ConsoleEmailSender + Protocol).
- [x] Invite link includes token as URL parameter.
- [x] Resending invite resets expiry (regenerates token + 72h TTL on same row).

## Notes

Self-service forgot-password email template is separate (TODO-033).
