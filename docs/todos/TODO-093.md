---
id: TODO-093
title: Auto-allocation algorithm (proportional/FIFO)
feature: FEAT-009
story: US-036
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-092]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-093 — Auto-allocation algorithm (proportional/FIFO)

## Description

Implement automatic payment allocation: proportional by default (amount split across line items by their ratio). FIFO as alternative.

## Acceptance criteria

- [ ] On payment recording: auto-create PaymentAllocations proportional to line item amounts.
- [ ] Proportional: each line item gets transaction.amount * (line_item.amount / invoice.total).
- [ ] Rounding handled (penny goes to largest line item).
- [ ] Auto-allocation overridable by manual allocation (TODO-094).

## Notes

