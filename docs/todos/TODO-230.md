---
id: TODO-230
title: Unblock service price updates when invoiced and synchronize ledger charges
story: US-079
feature: FEAT-029
status: done
priority: P0
dependencies: []
blocks: [TODO-231, TODO-232]
---

# TODO-230 - Unblock service price updates when invoiced and synchronize ledger charges

## Scope

- In `backend/app/services/projects.py:update_project_service_price`, remove the blocking 409 check that prevents updating service price when issued invoices exist.
- Update `ps.price_at_attachment` and synchronize the `LedgerEntry` charge for `PROJECT_SERVICE` to the new price.
- Keep audit log with `old_price` and `new_price`.
- Ensure open DRAFT invoices still update their line items accordingly.

## Acceptance check

- Service price can be updated even if an issued invoice exists on the project.
- The project service ledger charge reflects the new price.
