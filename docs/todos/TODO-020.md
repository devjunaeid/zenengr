---
id: TODO-020
title: Feature flag model (key-value per tenant, plan defaults)
feature: FEAT-003
story: US-010
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-012]
blocks: [TODO-021, TODO-022, TODO-023, TODO-024, TODO-025]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-020 — Feature flag model (key-value per tenant, plan defaults)

## Description

Create FeatureFlag model with per-tenant overrides and plan-level defaults. Flags: client_portal_payments, multi_service_projects, comments_module, partial_payment_tracking.

## Acceptance criteria

- [x] TenantFeatureFlag model: tenant_id FK, key, enabled (bool).
- [x] PlanFeatureDefault model: plan_id FK, key, enabled (bool).
- [x] Resolution order: tenant override > plan default > system default (false) — in `app/services/feature_flags.py`.
- [x] Adding new flag_key to DB makes it available without deploy (FR-3.5) — key is data-driven.
- [ ] Alembic migration seeds flag keys (defer to data seed script).

## Notes

