---
id: TODO-187
title: Statement aggregation & live financial service with Advance support
feature: FEAT-019
story: US-063
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-188, TODO-189]
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-187 — Statement aggregation & live financial service with Advance support

## Description

Implement/extend the project statement aggregation in `backend/app/services/ledger.py` to compile chronological entries for services (charges with date, name, quantity, unit price, amount) and payments/advances (date, method/reference, amount). Compute live totals: `total_charges`, `total_paid`, `net_due` ($\max(\text{Total Charges} - \text{Total Paid}, 0)$), and `advance_balance` ($\max(\text{Total Paid} - \text{Total Charges}, 0)$).

## Acceptance criteria

- [ ] Chronological entry list merging service charges and transaction payments/advances with accurate dates.
- [ ] Correct calculation of net due and advance balance (overpayment credit).
- [ ] Handles project discounts cleanly in the calculated totals.
