---
id: TODO-228
title: Frontend - allocation display, edit/delete with undo & restore, history panel, friendly warnings
story: US-078
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-222, TODO-227]
blocks: []
---

# TODO-228 - Frontend for FEAT-027

## Scope

- `lib/api/payments.js`; project ledger tab uses new payments endpoints.
- Ledger timeline: payment rows show allocated invoices + unallocated remainder (Advance chip); voided rows struck through with a `Restore` action.
- Edit payment dialog: all fields editable incl. allocations; inline warning when amount exceeds due ("Extra X will be kept as advance").
- Delete confirm: simple "Delete this payment?" with optional reason; after action show Undo toast (~8 s).
- Reusable `RecordHistory.svelte` drawer (who / when / before -> after) on payments, adjustments, purchases.
- Generate invoice: friendly "Everything is already billed" empty state.
- Invoice detail: payments list shows source payment with edit/delete/restore.

## Acceptance check

Manual browser verification on dev stack of AC-076.4, AC-077.1, AC-078.2..AC-078.5, AC-078.7; `npm run check` clean for touched files.
