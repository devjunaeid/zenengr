---
id: TODO-091
title: Payment recording UI
feature: FEAT-009
story: US-035
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-089]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-091 — Payment recording UI

## Description

Build payment recording form in Admin Portal invoice detail. Fields: amount, date, method, reference note.

## Acceptance criteria

- [x] "Record Payment" button/form on Issued invoice detail.
- [x] Amount field with validation (positive, <= balance due).
- [x] Method selector (bank transfer, card, cash, other).
- [x] Reference note text field.
- [x] After recording: invoice status updates immediately (TODO-090).
- [x] Payment history displayed below.

## Notes

Record payment dialog on invoice detail (issued/partially_paid only): amount, method (bank_transfer/card/cash/other), reference, date; transactions card with paid/balance summary + allocation breakdown.

