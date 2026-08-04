---
id: TODO-096
title: Project financial summary component
feature: FEAT-009
story: US-037
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-095]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-096 — Project financial summary component

## Description

Build reusable UI component for project financial summary cards (Total Invoiced, Total Paid, Outstanding Balance). Used in project overview (TODO-073).

## Acceptance criteria

- [x] Component displays 3 number cards with currency formatting.
- [x] Colors: total invoiced=blue, paid=green, outstanding=red.
- [x] Clicking "Outstanding" links to invoice list for that project.
- [x] Accepts financial data object as prop.

## Notes

Project detail page now shows live financial summary (total invoiced/paid/balance) + linked invoices list from overview endpoint.

