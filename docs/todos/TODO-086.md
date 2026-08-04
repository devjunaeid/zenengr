---
id: TODO-086
title: Download button in invoice views
feature: FEAT-008
story: US-033
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-085]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-086 — Download button in invoice views

## Description

Add PDF download button to invoice detail views in Admin Portal and Client Portal.

## Acceptance criteria

- [x] Download PDF button in Admin Portal invoice detail.
- [x] Download PDF button in Client Portal invoice detail (TODO-088).
- [x] Button triggers GET /api/tenant/invoices/{id}/pdf download.
- [x] Proper filename: {invoice_number}.pdf or draft-invoice-{id}.pdf.

## Notes

Download PDF buttons on staff + client invoice detail pages (fetch blob + a[download], filename from number, error banner).

