---
id: TODO-089
title: Transaction model + record API
feature: FEAT-009
story: US-035
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-075, TODO-078]
blocks: [TODO-090, TODO-091, TODO-092, TODO-095, TODO-098]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-089 — Transaction model + record API

## Description

Create Transaction model (invoice_id, amount, method, reference, recorded_by) + API to record payment against Issued invoice. Immutable after recording.

## Acceptance criteria

- [x] Transaction model: id, invoice_id FK, amount, method enum (bank_transfer/card/cash/other), reference_note, recorded_by_id FK, recorded_at, timestamps.
- [x] Alembic migration creates transactions table.
- [x] POST /api/tenant/invoices/{id}/transactions records payment.
- [x] Only Issued invoices accept payments.
- [x] Transaction immutable after recording (no edit/delete) (FR-9.6).
- [x] Action audited (TODO-042).

## Notes

Transaction + PaymentAllocation models + PaymentMethod enum + migration e5f6a7b8c9d0. POST /api/v1/tenant/invoices/{id}/transactions (manage/invoices) records payment; accepted on issued/partially_paid only (draft/paid/void 422). Immutable: no edit/delete endpoints. Audited invoice.payment_recorded.

