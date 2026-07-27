---
id: TODO-092
title: Payment allocation model
feature: FEAT-009
story: US-036
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-089]
blocks: [TODO-093, TODO-094]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-092 — Payment allocation model

## Description

Create PaymentAllocation model linking Transaction to InvoiceLineItems. Supports allocating partial payments across specific line items.

## Acceptance criteria

- [ ] PaymentAllocation model: transaction_id FK, line_item_id FK, amount.
- [ ] Sum of allocations = transaction amount.
- [ ] Each line item tracks paid_amount via sum of its allocations.
- [ ] Alembic migration.

## Notes

