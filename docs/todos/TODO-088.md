---
id: TODO-088
title: Client Portal invoice detail view
feature: FEAT-008
story: US-034
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-087]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-088 — Client Portal invoice detail view

## Description

Build Client Portal invoice detail showing line items, payment history, and PDF download.

## Acceptance criteria

- [x] GET /api/client/invoices/{id} returns invoice with line items and payment history.
- [x] Detail view: line items table, subtotal/tax/total, payment history list (FR-8.6).
- [x] PDF download button (TODO-086).
- [x] View-only, no edit.
- [x] Balance due displayed.

## Notes

Client invoice detail page: totals, paid/balance, line items, notes, PDF download, payment history.

