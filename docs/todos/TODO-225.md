---
id: TODO-225
title: Data migration with dry-run reconciliation report
story: US-076
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-221]
blocks: [TODO-226]
---

# TODO-225 - Payment & charge backfill migration

## Scope

- Script `backend/scripts/migrate_payments.py --dry-run|--commit [--tenant]`.
- Backfill: ledger PAYMENT rows → payments (link converted transaction via `source_id`); transactions without a payment → payment + allocation; detect statement "synced" copies (same project, amount, direction, method, recorded_at, reference) → mapped to the original payment, copy allocation flagged; `advances` → unallocated payment remainder; custom invoice lines on issued invoices → `invoice_line` charges.
- Report (CSV + console): per project old vs new paid/due/advance, duplicates found, over-allocations, overlapping statement invoices.
- Idempotent; original rows untouched.

## Acceptance check

Dry-run on dev DB produces a report; commit then re-run is a no-op; project summaries match report "new" values.
