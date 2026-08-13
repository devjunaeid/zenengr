---
id: TODO-178
title: LedgerEntry model + Project discount fields + migration
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-179, TODO-180, TODO-181]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-178 - LedgerEntry model + Project discount fields + migration

## Description

LedgerEntry model per FR-18.1: type (charge|payment|refund), source_type (project_service|transaction|manual_adjustment), source_id, invoice_ref (nullable), entry_date, created_by, append-only immutable (no update/delete). Indexes on (project_id, type) and (project_id, entry_date). Project gains discount_type (percentage|fixed|null), discount_value, discount_updated_at, discount_updated_by. Alembic migration.

## Acceptance criteria

- [x] LedgerEntry model with all fields + append-only enforcement. (FR-18.1)
- [x] Indexes: (project_id, type), (project_id, entry_date). (FR-18.1)
- [x] Project discount fields: discount_type/discount_value/discount_updated_at/discount_updated_by. (FR-18.3)
- [x] Migration up/down clean.

## Notes

- Shipped: LedgerEntry model (append-only, signed amounts) + Project discount fields; migration j6a7b8c9d0e1.
