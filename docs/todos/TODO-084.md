---
id: TODO-084
title: PDF generation service
feature: FEAT-008
story: US-033
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-075]
blocks: [TODO-085]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-084 — PDF generation service

## Description

Build server-side PDF generation service for invoices. Template-based (e.g., WeasyPrint, pdfkit, or headless browser). Renders invoice layout with all fields.

## Acceptance criteria

- [x] GET /api/tenant/invoices/{id}/pdf returns downloadable PDF.
- [x] PDF includes: invoice number, issue date, due date, line items, subtotal, tax, total, company info (FR-8.2).
- [x] Draft invoice PDF optionally watermarked "DRAFT" (FR-8.7).
- [x] Client Portal also has PDF download (TODO-086).
- [x] PDF generation is server-side, not client-side.

## Notes

reportlab 5.0 added; app/services/pdf.py renders A4 invoice PDF (header, line items, totals, notes, footer).
