---
id: TODO-032
title: Admin-triggered password reset API
feature: FEAT-004
story: US-014
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-033]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-032 — Admin-triggered password reset API

## Description

Build endpoint for Tenant Admin to trigger password reset for another active admin user. Distinct from self-service forgot-password. Audited.

## Acceptance criteria

- [ ] POST /api/tenant/users/{id}/reset-password sends reset email (FR-4.12).
- [ ] Only works for active users (not deactivated) (FR-4.11).
- [ ] Action audited (TODO-042).
- [ ] Reset email uses distinct template (TODO-033).
- [ ] Tenant Admin cannot trigger reset for users in other tenants.

## Notes

