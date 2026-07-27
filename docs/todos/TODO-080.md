---
id: TODO-080
title: Lock enforcement on Issued invoices
feature: FEAT-008
story: US-031
status: proposed
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

- [ ] PATCH on Issued invoice's financial fields returns 422.
- [ ] Issued invoice cannot be deleted (405 Method Not Allowed).
- [ ] Only status transition allowed: Issued -> Void (TODO-081).
- [ ] Server-side enforcement (not just UI).

## Notes

