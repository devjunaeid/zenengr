---
id: TODO-154
title: Transaction direction debit/credit + refund endpoint
feature: FEAT-015
story: US-057
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-155]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-154 - Transaction direction debit/credit + refund endpoint

## Description

Add direction enum (DEBIT = money in / receipt, CREDIT = money out / refund) to Transaction (+ migration). Add `POST /tenant/invoices/{id}/refund` creating a credit entry (reversing an applied payment or reducing advance). Amounts immutable after recording. Audited. Tests.

## Acceptance criteria

- [x] Direction enum DEBIT/CREDIT on Transaction + migration. (FR-15.2)
- [x] Refund endpoint creates credit entry. (FR-15.2)
- [x] Amounts immutable after recording. (FR-15.2)
- [x] Refund audited. (FR-15.2)
- [x] Tests green.

## Notes

- Shipped: Transaction.direction DEBIT/CREDIT; POST /tenant/invoices/{id}/refund creates credit entry (amount <= paid, 422 otherwise); amounts immutable; audited.
