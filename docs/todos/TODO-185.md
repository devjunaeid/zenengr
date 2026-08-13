---
id: TODO-185
title: Invoice generator + invoice_ref tagging
feature: FEAT-018
story: US-062
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-180]
blocks: [TODO-186]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-185 - Invoice generator + invoice_ref tagging

## Description

Generator UI (project pre-selected or fully custom scope; NO multi-project). Service picker flags already-invoiced services. Discount added as negative line item when project has discount, so document matches Summary. On issue: tag covered ProjectService charge entries (invoice_ref) — backend change in issue_invoice. Badge "Included in INV-…" on timeline. Client portal lists issued invoices.

## Acceptance criteria

- [x] Generator: single-project scope (pre-selected) OR fully custom line items; no multi-project. (FR-18.7)
- [x] Service picker flags already-invoiced services. (FR-18.7)
- [x] Discount as negative line item on discounted projects. (FR-18.7)
- [x] Draft then issue (existing invoice flow). (FR-18.7)
- [x] On issue, covered charges get invoice_ref tag (issue_invoice backend change). (FR-18.8)
- [x] Badge "Included in INV-…" on timeline; client portal lists issued invoices. (FR-18.8, FR-18.9)

## Notes

- Shipped: generator flags already-invoiced services, discount as negative line item, invoice_ref tagging at issue.
