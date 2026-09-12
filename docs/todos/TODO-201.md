---
id: TODO-201
title: Backend service price update API and draft invoice sync
story: US-067
feature: FEAT-022
status: done
priority: P0
---

# TODO-201 — Backend service price update API and draft invoice sync

## Context

When an admin attaches a service with a wrong price or makes a typo during project creation, there is currently no way to update `ProjectService.price_at_attachment`.

## Requirements

1. Add `PATCH /tenant/projects/{project_id}/services/{project_service_id}` endpoint in `backend/app/api/v1/projects.py`.
2. Schema `ProjectServiceUpdateRequest` in `backend/app/schemas/projects.py` with `price: Decimal` (must be >= 0).
3. In `backend/app/services/projects.py`, add `update_project_service_price`:
   - Validate project and service belong to tenant.
   - Check if the service charge is already locked by an issued invoice (`invoice_ref` pointing to non-draft invoice). If so, raise HTTP 409 Conflict.
   - Update `ProjectService.price_at_attachment = price`.
   - Update corresponding `LedgerEntry` (`type == CHARGE`, `source_type == PROJECT_SERVICE`, `source_id == project_service.id`) to `amount = price`.
   - Update any DRAFT invoice line items in this project referencing `project_service_id` (`unit_price = price`, `amount = price * quantity`).
   - Audit log `project.service_price_updated`.
4. Unit/integration tests covering successful price update, ledger sync, draft invoice sync, and issued invoice lock guard.
