---
id: TODO-099
title: Client Portal outstanding balance display
feature: FEAT-009
story: US-038
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-098]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-099 — Client Portal outstanding balance display

## Description

Show outstanding balance per invoice and as client total in Client Portal. Computed = sum(invoice totals) - sum(payments).

## Acceptance criteria

- [x] Each invoice in list shows balance due.
- [x] Client total outstanding displayed on dashboard/header.
- [x] Live computed from transaction data (FR-9.5).

## Notes

Outstanding balance (paid_amount/balance_due) shown on client invoice detail + project financial summary.

