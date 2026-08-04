---
id: TODO-098
title: Client Portal payment history view
feature: FEAT-009
story: US-038
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-089, TODO-038]
blocks: [TODO-099]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-098 — Client Portal payment history view

## Description

Build Client Portal payment history tab showing transaction records for the client's invoices. Read-only.

## Acceptance criteria

- [x] GET /api/client/transactions returns payments for Client User's client invoices.
- [x] List: transaction date, amount, method, reference note (FR-9.5).
- [x] View-only — no record or modify (FR-9.5).
- [x] Only own client's payments visible (FR-4.8).

## Notes

Payment history table on client invoice detail (GET /client/invoices/{id}/transactions, allocations expandable).

