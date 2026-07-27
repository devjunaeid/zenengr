---
id: TODO-004
title: Create Tenant model + migration
feature: FEAT-001
story: US-004
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-005, TODO-006, TODO-007, TODO-008, TODO-009, TODO-010, TODO-012, TODO-015, TODO-016, TODO-017, TODO-020, TODO-026, TODO-029, TODO-030, TODO-032, TODO-034, TODO-037, TODO-038, TODO-040, TODO-043, TODO-056, TODO-062, TODO-075, TODO-100, TODO-109, TODO-113, TODO-114, TODO-116, TODO-119]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-004 — Create Tenant model + migration

## Description

Create SQLAlchemy Tenant model (business name, slug, status enum, plan FK, timestamps) + Alembic migration. Enforce unique slug constraint. Model tenant isolation at the ORM level (tenant_id column pattern or row-level security design).

## Acceptance criteria

- [x] Tenant model with fields: id, business_name, slug (unique), status (Trial/Active/Suspended/Cancelled), plan_id FK, contact_info JSON, created_at, updated_at.
- [x] Alembic migration creates `tenants` table.
- [x] Slug validated as unique at DB level (unique index).
- [x] Model includes tenant isolation strategy (e.g., tenant_id on all scoped tables).
- [x] Reviewed against `docs/backend-standard.md`.

## Notes

Foundation model — most feature tables depend on tenant_id column.
