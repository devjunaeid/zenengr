---
id: TODO-084
title: PDF generation service
feature: FEAT-008
story: US-033
status: proposed
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

- [ ] GET /api/tenant/invoices/{id}/pdf returns downloadable PDF.
- [ ] PDF includes: invoice number, issue date, due date, line items, subtotal, tax, total, company info (FR-8.2).
- [ ] Draft invoice PDF optionally watermarked "DRAFT" (FR-8.7).
- [ ] Client Portal also has PDF download (TODO-086).
- [ ] PDF generation is server-side, not client-side.

## Notes

Consider library choice based on deployment constraints.
