---
id: TODO-098
title: Client Portal payment history view
feature: FEAT-009
story: US-038
status: proposed
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

- [ ] GET /api/client/transactions returns payments for Client User's client invoices.
- [ ] List: transaction date, amount, method, reference note (FR-9.5).
- [ ] View-only — no record or modify (FR-9.5).
- [ ] Only own client's payments visible (FR-4.8).

## Notes

