---
id: TODO-180
title: Summary + ledger timeline service
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-178, TODO-179]
blocks: [TODO-182, TODO-185]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-180 - Summary + ledger timeline service

## Description

get_project_ledger(session, tenant_id, project_id) → {entries (merged charges + transaction-derived payments/refunds, chronological), summary {subtotal, discount_value, discount_type, discount_amount, total, paid, due}}. Discount math per FR-18.4: percentage → round(Subtotal × v / 100, 2); fixed → min(v, Subtotal); Paid = Σ payments − Σ refunds (transaction stream incl. advances via allocations); Due = max(Total − Paid, 0).

## Acceptance criteria

- [x] Entries: charges + derived payments/refunds merged, chronological. (FR-18.2, FR-18.4)
- [x] Summary fields: subtotal, discount_value, discount_type, discount_amount, total, paid, due. (FR-18.4)
- [x] Discount math exact per FR-18.4 (percentage rounds 2dp; fixed caps at Subtotal; Due = max(Total − Paid, 0)). (FR-18.4)

## Notes

- Shipped: payment stream derived from Transactions at read time (no mirror); live Summary per FR-18.4.
