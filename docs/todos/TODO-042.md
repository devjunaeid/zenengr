---
id: TODO-042
title: Instrument sensitive actions with audit logging
feature: FEAT-004
story: US-017
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-040]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-042 — Instrument sensitive actions with audit logging

## Description

Add audit log calls at each sensitive action: role changes, deactivations, invoice issuance, payment recording. Scope: FR-4.13 actions.

## Acceptance criteria

- [x] Role change (TODO-029) creates audit entry — **done** (`user.role_changed` with from/to details).
- [x] Deactivation/reactivation (TODO-030) creates audit entry — **done** (`user.deactivated`, `user.reactivated`).
- [ ] Invoice issue (TODO-078) creates audit entry — **pending** (later batch).
- [ ] Payment recording (TODO-089) creates audit entry — **pending** (later batch).
- [x] Admin-triggered password reset (TODO-032) creates audit entry — **done** (`user.password_reset_initiated`, `user.password_reset_completed`).
- [x] Each entry: who, what action, timestamp, entity ID — **done**.
- [ ] All existing audit points covered before marking done.

## Notes

User-admin actions instrumented: role_changed, deactivated, reactivated, password_reset_initiated, password_reset_completed.
Invoice/payment hooks remain in TODO-078/TODO-089 batches.
