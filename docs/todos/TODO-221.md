---
id: TODO-221
title: Payment model, payment_id on transactions, void columns & Alembic migration (schema only)
story: US-076
feature: FEAT-027
status: done
priority: P0
dependencies: []
blocks: [TODO-222, TODO-223, TODO-225]
---

# TODO-221 - Payment model & schema migration

## Context

Payments currently live in `ledger_entries` (type PAYMENT) and `transactions`, merged by a heuristic in `services/ledger.py`.

## Scope

- New `app/models/payment.py`: `Payment` per FR-27.1 (kind receipt|refund, amount>0, method, paid_on, reference, notes, client_id, project_id nullable, voided_at/by/reason).
- `transactions.payment_id` (nullable FK for now; required by service for new rows), `transactions.voided_at`.
- `ledger_entries`: add `voided_at`, `voided_by_id`, `void_reason`; add `LedgerSourceType.INVOICE_LINE`.
- Indexes: `(tenant_id, project_id, paid_on)`, `(client_id)`.
- Alembic revision (schema only, no data move).

## Acceptance check

`uv run alembic upgrade head` and `downgrade -1` both succeed; models import cleanly; existing tests still pass for touched modules.
