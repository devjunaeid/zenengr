---
id: TODO-017
title: Tenant settings model + permission matrix
feature: FEAT-002
story: US-009
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-016]
blocks: [TODO-018, TODO-019, TODO-079]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-017 — Tenant settings model + permission matrix

## Description

Create TenantSettings model with key-value pairs plus permission matrix defining who can edit each setting (SuperAdminOnly / TenantAdminEditable / TenantAdminViewOnly). Settings: default currency, invoice numbering format, timezone, date format, email sender identity.

## Acceptance criteria

- [x] TenantSettings model: tenant_id, key, value, permission_level enum.
- [ ] Permission matrix enforced server-side (FR-2.5) — model supports, enforcement awaits service layer.
- [x] Invoice numbering format stored as template (INV-{YYYY}-{SEQ:04d}).
- [x] Seed default settings defined in DEFAULT_SETTINGS constant.
- [ ] Super Admin can edit all settings; Tenant Admin edits only editable ones — API-layer concern.

## Notes

