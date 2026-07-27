---
id: TODO-016
title: Subscription status model
feature: FEAT-002
story: US-008
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-012]
blocks: [TODO-017]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-016 — Subscription status model

## Description

Create Subscription model linking tenant to plan with status enum (active, past_due, cancelled), billing cycle, renewal date. Separate from tenant status.

## Acceptance criteria

- [x] Subscription model: tenant_id FK, plan_id FK, status enum, billing_cycle, renewal_date, timestamps.
- [x] Alembic migration.
- [x] Tenant has one subscription record at a time (unique constraint).
- [ ] Status transitions tracked for audit (service-level — add when instrumentation is built).

## Notes

