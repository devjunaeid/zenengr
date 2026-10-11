---
id: TODO-231
title: Unify payment accounting in compute_project_ledger_summary and get_project_ledger
story: US-079
feature: FEAT-029
status: done
priority: P0
dependencies: [TODO-230]
blocks: [TODO-232]
---

# TODO-231 - Unify payment accounting in compute_project_ledger_summary and get_project_ledger

## Scope

- In `backend/app/services/ledger.py:compute_project_ledger_summary`, remove the exclusive `if direct_payments: ... else: ...` branch.
- Unify payment discovery: combine direct `Payment` records (where `project_id == project.id`) and non-draft invoice `Transaction` records, deduplicating them so transactions linked to payments are not double-counted.
- Ensure `paid = payments - refunds`, `due = max(total - paid, 0)`, and `advance_balance = max(paid - total, 0)` are always mathematically sound and match the ledger timeline entries.

## Acceptance check

- Projects with direct payments, invoice transactions, or both calculate `paid` and `due` consistently without omission or duplication.
