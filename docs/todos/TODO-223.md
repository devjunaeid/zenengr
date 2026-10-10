---
id: TODO-223
title: Ledger summary & timeline rewritten on payments (remove heuristic dedup)
story: US-076
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-221, TODO-222]
blocks: [TODO-224, TODO-226]
---

# TODO-223 - Ledger read model on payments

## Scope

- `compute_project_ledger_summary`: charges = Σ active `LedgerEntry` CHARGE rows; paid = Σ active receipts − refunds from `payments`; remove custom-line side query, `ps_fallback`, "synced" filter and signature dedup.
- `get_project_ledger`: entries = charges + payments (with allocation invoice numbers) + void info.
- `financials.py`, `transactions.build_client_ledger`, `pdf.py` statement use the same summary.
- Client advance = Σ unallocated active payments for the client.

## Acceptance check

`tests/test_ledger_api.py`, `tests/test_statement_invoices_api.py` updated and passing; no reference to "synced" remains in services.
