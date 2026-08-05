---
id: TODO-156
title: Apply-advance endpoint
feature: FEAT-015
story: US-057
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-155]
blocks: [TODO-157, TODO-159]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-156 - Apply-advance endpoint

## Description

`POST /tenant/invoices/{id}/apply-advance {amount?}` moves client advance (or unassigned advance for general invoices) onto the invoice as a payment/allocation. Invoice status recomputes (partially_paid/paid). Audited. Tests.

## Acceptance criteria

- [x] Endpoint applies advance (optional amount, default full). (FR-15.4)
- [x] Uses client advance for client/project invoices; unassigned advance for general invoices. (FR-15.4)
- [x] Invoice status recomputes (partially_paid/paid). (FR-15.4)
- [x] Audited. (FR-15.4)
- [x] Tests green.

## Notes

- Shipped: POST /tenant/invoices/{id}/apply-advance (manual, optional amount default full, oldest-first proportional allocations, invoice status recompute); audited.
