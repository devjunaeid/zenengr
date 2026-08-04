---
id: TODO-080
title: Lock enforcement on Issued invoices
feature: FEAT-008
story: US-031
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-078]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-080 — Lock enforcement on Issued invoices

## Description

Ensure issued invoices cannot be edited on financial fields (line items, amounts, dates). Only void/cancel allowed. Corrections via new documents (FR-8.4).

## Acceptance criteria

- [x] PATCH on Issued invoice's financial fields returns 422.
- [x] Issued invoice cannot be deleted (405 Method Not Allowed).
- [x] Only status transition allowed: Issued -> Void (TODO-081).
- [x] Server-side enforcement (not just UI).

## Notes

Lock enforcement complete: financial PATCH on issued -> 422 (notes-only allowed), DELETE issued -> 405, void transition via POST /{id}/void (TODO-081), all server-side.
