---
id: TODO-222
title: Payments service & API (record, allocate, auto-allocate, void, edit)
story: US-076
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-221]
blocks: [TODO-224, TODO-226, TODO-228]
---

# TODO-222 - Payments service & API

## Scope

- `app/services/payments.py`: `record_payment`, `allocate_payment`, `auto_allocate` (oldest open invoice first), `void_payment` (optional reason, voids allocations, recomputes invoice status), `restore_payment`, `update_payment` (amount/date/method/reference/notes/allocations; amount below allocated total requires releasing allocations), `unallocated_amount`.
- Row lock on payment during allocation; allocation sum ≤ amount.
- Endpoints: `POST/GET /tenant/projects/{id}/payments`, `POST /tenant/payments/{id}/allocations`, `POST /tenant/payments/{id}/void`, `POST /tenant/payments/{id}/restore`, `PATCH /tenant/payments/{id}`.
- Rewire existing `record_transaction` (invoice page) and `add_project_payment` to call the new service, keeping their response contracts.
- `apply_advance` → allocate unallocated payment.
- Audit events: `payment.recorded|allocated|voided|updated` with before/after.
- Tests: `tests/test_payments_api.py` (same-amount same-day, over-allocation 422, void recompute, overpay remainder).

## Acceptance check

AC-076.2..AC-076.5 covered by tests; `tests/test_transactions_api.py` and `tests/test_project_payments_api.py` pass.
