---
id: TODO-155
title: Advance model + overpay split
feature: FEAT-015
story: US-057
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-154]
blocks: [TODO-156, TODO-157]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-155 - Advance model + overpay split

## Description

Advance record (client_id nullable = unassigned, amount, applied/refunded tracking or computed). `record_transaction` splits overpay into advance: applied portion covers the invoice, excess becomes ADVANCE (client-scoped for client/project invoices; unassigned for general invoices). Tests.

## Acceptance criteria

- [x] Advance model: client_id nullable (unassigned), amount, applied/refunded tracking. (FR-15.3)
- [x] record_transaction splits overpay into advance. (FR-15.3)
- [x] Advance client-scoped for client/project invoices; unassigned for general invoices. (FR-15.3)
- [x] Tests green.

## Notes

- Shipped: Advance model + PaymentAllocation.advance_id + migration a0b1c2d3e4f5; overpay splits into advance (client-scoped or unassigned).
