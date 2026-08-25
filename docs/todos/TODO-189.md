---
id: TODO-189
title: Cumulative statement invoice generation & issue endpoint
feature: FEAT-019
story: US-064
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-187]
blocks: [TODO-190, TODO-192]
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-189 — Cumulative statement invoice generation & issue endpoint

## Description

Create `POST /api/v1/tenant/projects/{id}/generate-statement-invoice`.
Generates and issues a formal statement invoice:
- Captures all chronological project charges and payment records into invoice line items / statement breakdown.
- Assigns the next sequential `invoice_number` (`INV-XXXX`) under lock.
- Computes `subtotal`, `tax_total`, `total`, `paid`, and `balance_due` / `advance_credit`.
- Tags covered project ledger charges with `invoice_ref`.
- Emits audit log and notification events.

## Acceptance criteria

- [ ] Generates an issued invoice with progressive history.
- [ ] Tags ledger charges with the new invoice reference.
- [ ] Accessible by staff with `invoices:create` permission.
