---
id: TODO-081
title: Void invoice API + status update
feature: FEAT-008
story: US-032
status: done
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

- [x] POST /api/tenant/invoices/{id}/void sets status=Void (FR-8.3).
- [x] Voided invoice retains invoice_number and all original data (FR-8.4).
- [x] Void action audited (TODO-042).
- [x] Only Tenant Admin/Manager can void.
- [x] Already-void invoices return 422.

## Notes

POST /api/v1/tenant/invoices/{id}/void (manage/invoices). Source statuses issued/partially_paid/paid -> void; draft -> 422 (delete instead); already-void -> 422. Number + all data retained. Audited invoice.voided.
