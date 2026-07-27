---
id: TODO-075
title: Invoice model with line items
feature: FEAT-008
story: US-030
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-043]
blocks: [TODO-076, TODO-079, TODO-084, TODO-087, TODO-089]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-075 — Invoice model with line items

## Description

Create Invoice model (tenant_id, project_id, invoice_number nullable, status, issue_date, due_date, subtotal, tax, total) + InvoiceLineItem model. Draft invoices have no number.

## Acceptance criteria

- [ ] Invoice model: id, tenant_id FK, project_id FK, invoice_number (nullable), status enum (Draft/Issued/Paid/PartiallyPaid/Void), issue_date, due_date, subtotal, tax_total, total, timestamps.
- [ ] InvoiceLineItem: id, invoice_id FK, description, quantity, unit_price, amount, service_id FK nullable, project_service_id FK nullable.
- [ ] Alembic migration creates both tables.
- [ ] Invoice number NOT assigned until Issued (Draft nullable).
- [ ] Project can have multiple invoices (FR-8.5).

## Notes

