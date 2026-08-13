---
id: TODO-169
title: Notification model + migration
feature: FEAT-017
story: US-059
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-168]
blocks: [TODO-170, TODO-172]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-169 - Notification model + migration

## Description

Create Notification model as designed: id, user_id, user_type, tenant_id, event_type, title, body, entity_type, entity_id, data JSONB, is_read, created_at. History retained (rows never deleted); read state per user. Indexes on (user_id, tenant, created_at). Alembic migration.

## Acceptance criteria

- [x] Notification model matches design: id, user_id, user_type, tenant_id, event_type, title, body, entity_type, entity_id, data JSONB, is_read, created_at. (FR-17.2)
- [x] Indexes: user_id, tenant, created_at. (FR-17.2)
- [x] Migration creates table; history retained; read state per user. (FR-17.2)

## Notes

- Rows are append-only (no delete of history); is_read is the only mutable state.
- Shipped: Notification model (id, user_id, user_type, tenant_id, event_type, title, body, entity_type, entity_id, data JSONB, is_read, created_at) + migration; indexes (user_id, tenant, created_at); history append-only.
