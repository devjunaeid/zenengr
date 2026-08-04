---
id: TODO-082
title: Voided invoice display state
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

# TODO-082 — Voided invoice display state

## Description

Show voided invoices with visible "VOID" watermark/overlay in invoice views. Retain all data for audit.

## Acceptance criteria

- [x] Voided invoices show prominent "Void" badge/overlay in list and detail views.
- [x] All original data still visible.
- [x] No edit actions available on voided invoices.

## Notes

Voided invoices show void status badge (StatusBadge) in list + detail; retained number + data; hidden from client portal invoice list (kept in tenant list).

