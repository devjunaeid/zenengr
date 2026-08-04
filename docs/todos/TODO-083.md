---
id: TODO-083
title: Correction workflow guidance in UI
feature: FEAT-008
story: US-032
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-081]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-083 — Correction workflow guidance in UI

## Description

Show UI guidance on voided invoice: "To correct this invoice, create a new invoice referencing the voided one." Link to create new invoice.

## Acceptance criteria

- [x] Voided invoice detail shows guidance message.
- [x] "Create new invoice for this project" button/action.
- [x] New invoice can reference voided invoice number in notes.

## Notes

Voided invoice detail shows correction guidance card + Create new invoice button (preselects project_id). MVP corrections via new invoice; credit notes Phase 2 (FEAT-008 decision).

