---
id: TODO-043
title: Client model + CRUD API
feature: FEAT-005
story: US-018
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-044, TODO-045, TODO-046, TODO-048, TODO-049, TODO-051, TODO-054, TODO-062, TODO-075]
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-043 — Client model + CRUD API

## Description

Create Client model (tenant_id, name, contact info, billing address, tax ID, status) + CRUD API. Client names unique within tenant.

## Acceptance criteria

- [ ] Client model: id, tenant_id FK, name, contact_info JSON, billing_address, tax_id, status (Active/Archived), timestamps.
- [ ] Alembic migration creates clients table.
- [ ] POST/GET/PATCH /api/tenant/clients CRUD.
- [ ] Client name unique per tenant.
- [ ] Tenant Admin/Manager can create/edit (FR-5.1). Employee view-only (FR-4.2).
- [ ] Multiple Client Users per client with single primary billing contact (FR-5.3).

## Notes

