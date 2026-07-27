---
id: TODO-091
title: Payment recording UI
feature: FEAT-009
story: US-035
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-089]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-091 — Payment recording UI

## Description

Build payment recording form in Admin Portal invoice detail. Fields: amount, date, method, reference note.

## Acceptance criteria

- [ ] "Record Payment" button/form on Issued invoice detail.
- [ ] Amount field with validation (positive, <= balance due).
- [ ] Method selector (bank transfer, card, cash, other).
- [ ] Reference note text field.
- [ ] After recording: invoice status updates immediately (TODO-090).
- [ ] Payment history displayed below.

## Notes

