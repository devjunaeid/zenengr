---
id: TODO-094
title: Allocation override UI
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

# TODO-094 — Allocation override UI

## Description

Build UI for manual override of payment allocation across line items. Staff can enter per-line-item amounts.

## Acceptance criteria

- [ ] Payment recording form includes allocation table (only if multi-line-item invoice).
- [ ] Auto-calculated proportions shown as defaults.
- [ ] Staff can enter custom amounts per line item (must sum to payment total).
- [ ] Validation: sum of allocations = transaction amount.
- [ ] Changing allocation updates line-item-level paid amounts (FR-9.3).

## Notes

