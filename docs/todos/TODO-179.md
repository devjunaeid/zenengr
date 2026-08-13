---
id: TODO-179
title: Charge hooks + reversal + manual adjustment
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-178]
blocks: [TODO-180]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-179 - Charge hooks + reversal + manual adjustment

## Description

Attaching a ProjectService writes a `charge` LedgerEntry (amount = price at attachment, entry_date = today). Cancelling/removing a service writes an offsetting adjustment entry (keeps ledger honest). POST /tenant/projects/{id}/ledger/adjustments (admin/manager only, audited) creates a `manual_adjustment` entry.

## Acceptance criteria

- [x] Service attach → charge entry (amount = price_at_attachment, entry_date = today). (FR-18.5)
- [x] Service cancel/removal → offsetting adjustment entry. (FR-18.5)
- [x] POST /tenant/projects/{id}/ledger/adjustments: admin/manager only, audited, creates manual_adjustment entry. (FR-18.6)

## Notes

- Shipped: service attach charges, cancel/removal reversals, audited manual adjustment endpoint (append-only).
