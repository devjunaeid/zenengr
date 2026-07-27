---
id: TODO-078
title: Issue invoice API (number assignment + field lock)
feature: FEAT-008
story: US-031
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-076, TODO-079]
blocks: [TODO-080, TODO-081]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-078 — Issue invoice API (number assignment + field lock)

## Description

Build POST /api/tenant/invoices/{id}/issue endpoint. Assigns tenant-scoped sequential invoice number (via TODO-079), locks all core financial fields, transitions status to Issued.

## Acceptance criteria

- [ ] POST /api/tenant/invoices/{id}/issue assigns invoice_number from sequence generator.
- [ ] Locking: subsequent PATCH on financial fields returns 422.
- [ ] Status transitions Draft -> Issued (FR-8.3).
- [ ] Non-financial fields (notes, memo) may still be editable after issue (per ADR).
- [ ] Action audited (TODO-042).

## Notes

