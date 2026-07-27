---
id: TODO-040
title: Audit log model + service
feature: FEAT-004
story: US-017
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-041, TODO-042]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-040 — Audit log model + service

## Description

Create AuditLog model (tenant_id, actor_id, action, entity_type, entity_id, details JSON, timestamp). Append-only service. Super Admin and Tenant Admin can view.

## Acceptance criteria

- [x] AuditLog model: id, tenant_id, actor_id, action, entity_type, entity_id, details (JSON), created_at.
- [x] Append-only — no update/delete columns (no updated_at).
- [x] Service method: log_action(...) — service layer scaffolded.
- [x] Alembic migration creates audit_logs table.

## Notes

MVP scope: role changes, deactivations, invoice issuance, payment recording (FR-4.13).
