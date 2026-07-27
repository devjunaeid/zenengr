---
id: TODO-076
title: Draft invoice create API
feature: FEAT-008
story: US-030
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-075]
blocks: [TODO-077, TODO-078]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-076 — Draft invoice create API

## Description

Build POST endpoint to create Draft invoice. Select project services as line items or add custom line items. Drafts fully editable.

## Acceptance criteria

- [ ] POST /api/tenant/invoices creates Draft invoice with line items.
- [ ] Line items can reference ProjectService IDs or be custom (description + amount).
- [ ] Draft invoice: issue_date and due_date set by user. invoice_number=null.
- [ ] Draft invoices fully editable (line items, amounts, dates) (FR-8.4).
- [ ] Only Tenant Admin/Manager can create invoices.

## Notes

