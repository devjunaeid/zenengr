---
id: TODO-012
title: Subscription Plan model + CRUD
feature: FEAT-002
story: US-007
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-013, TODO-014, TODO-015, TODO-016, TODO-020, TODO-022]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-012 — Subscription Plan model + CRUD

## Description

Create Plan model with configurable resource limits. Super Admin CRUD for subscription plans. Limits are data-driven — no redeploy needed on change.

## Acceptance criteria

- [x] Plan model: id, name, description, max_admin_users, max_clients, max_active_projects, max_storage_mb, is_active, timestamps.
- [x] Alembic migration creates plans table.
- [ ] Super Admin CRUD API + UI for plans (API pending — next sprint).
- [ ] Delete is soft (is_active=false) if tenants assigned (service-level).
- [x] Limits stored as integers, enforced at runtime (linked to TODO-013).

## Notes

