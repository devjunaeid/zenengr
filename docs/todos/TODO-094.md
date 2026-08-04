---
id: TODO-094
title: Allocation override UI
feature: FEAT-009
story: US-036
status: done
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

- [x] Payment recording form includes allocation table (only if multi-line-item invoice).
- [x] Auto-calculated proportions shown as defaults.
- [x] Staff can enter custom amounts per line item (must sum to payment total).
- [x] Validation: sum of allocations = transaction amount.
- [x] Changing allocation updates line-item-level paid amounts (FR-9.3).

## Notes

Manual allocation mode in record-payment dialog (per-line-item amounts, cents-sum validation, server 422 surfaced). Auto proportional remains default.

