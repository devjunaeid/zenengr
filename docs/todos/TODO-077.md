---
id: TODO-077
title: Draft invoice editor UI
feature: FEAT-008
story: US-030
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-076]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-077 — Draft invoice editor UI

## Description

Build draft invoice editor in Admin Portal: add/remove line items, adjust amounts, set dates. Live subtotal/tax/total calculation.

## Acceptance criteria

- [x] Invoice editor with line items table: add/remove rows.
- [x] Service selector to add project service as line item.
- [x] Custom line item row: description + amount fields.
- [x] Live calculation of subtotal, tax, total.
- [x] Save as Draft (PATCH) or Issue (TODO-078).

## Notes

Draft invoice editor (new + edit pages): project select w/ ?project_id preselect, dynamic line items (project-service or custom rows, computed amounts), dates/notes, totals footer, issue/void/delete actions with ConfirmDialogs.

