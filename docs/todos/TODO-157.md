---
id: TODO-157
title: Client advance balance + ledger API (staff)
feature: FEAT-015
story: US-057
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-155, TODO-156]
blocks: [TODO-158, TODO-159]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-157 - Client advance balance + ledger API (staff)

## Description

Compute client advance balance = advances - applied - refunded live from ledger; expose on client detail (staff). Staff client detail shows Ledger of debit/credit entries with running balance. Tests.

## Acceptance criteria

- [x] Advance balance computed live from ledger. (FR-15.5)
- [x] Advance balance on client detail (staff). (FR-15.5)
- [x] Ledger of Dr/Cr entries with running balance on client detail (staff). (FR-15.6)
- [x] Invoice status auto-update accounts for advances. (FR-15.6)
- [x] Tests green.

## Notes

- Shipped: GET /tenant/clients/{id}/ledger (Dr/Cr + running balance + advance_balance); financials paid = allocations - credits.
