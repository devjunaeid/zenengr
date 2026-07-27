---
id: TODO-081
title: Void invoice API + status update
feature: FEAT-008
story: US-032
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-078]
blocks: [TODO-082, TODO-083]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-081 — Void invoice API + status update

## Description

Build POST /api/tenant/invoices/{id}/void endpoint. Voided invoice retains number and all data. Status set to Void. Audited.

## Acceptance criteria

- [ ] POST /api/tenant/invoices/{id}/void sets status=Void (FR-8.3).
- [ ] Voided invoice retains invoice_number and all original data (FR-8.4).
- [ ] Void action audited (TODO-042).
- [ ] Only Tenant Admin/Manager can void.
- [ ] Already-void invoices return 422.

## Notes

MVP corrections: new invoice referencing voided one. Credit notes Phase 2.
