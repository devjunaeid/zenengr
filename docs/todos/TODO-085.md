---
id: TODO-085
title: PDF template with invoice layout
feature: FEAT-008
story: US-033
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-084]
blocks: [TODO-086]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-085 — PDF template with invoice layout

## Description

Design and implement invoice PDF template with tenant branding (logo, colors). Professional layout showing all invoice fields.

## Acceptance criteria

- [x] Template uses tenant logo and branding colors (TODO-011).
- [x] Layout: header (logo + company info), line items table, totals section, footer.
- [x] "DRAFT" watermark on draft invoices.
- [x] Responsive to variable line item count (multi-page if needed).

## Notes

Template: tenant business name, invoice number or DRAFT, status, project/client, issue/due dates, line items table, subtotal/tax/total, notes, Generated-by footer. Monochrome.

