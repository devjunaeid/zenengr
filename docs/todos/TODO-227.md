---
id: TODO-227
title: Soft delete + restore, record history API & audit for purchases
story: US-078
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-221]
blocks: [TODO-228]
---

# TODO-227 - Auditable corrections (backend)

## Scope

- Adjustment/payment `DELETE` endpoints become soft delete (void, optional `reason`); add `POST .../restore` endpoints.
- Every update writes audit details `{before: {...}, after: {...}}`.
- `GET /tenant/audit/{entity_type}/{entity_id}` returns record history (permission: view financial records).
- `api/v1/purchase_entries.py`: audit `purchase.created|updated|deleted` with before/after totals and items.
- Tests in `tests/test_financial_corrections_api.py`.

## Acceptance check

AC-078.1..AC-078.3, AC-078.5, AC-078.6 covered by tests.
