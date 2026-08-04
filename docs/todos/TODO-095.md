---
id: TODO-095
title: Financial rollup computation service
feature: FEAT-009
story: US-037
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-089]
blocks: [TODO-046, TODO-072, TODO-096, TODO-097]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-095 — Financial rollup computation service

## Description

Build service computing financial rollups from live invoice/transaction data: Total Invoiced, Total Paid, Total Outstanding per project and per client.

## Acceptance criteria

- [x] Service method: get_project_financials(project_id) -> {total_invoiced, total_paid, total_outstanding}.
- [x] Service method: get_client_financials(client_id) -> {total_invoiced, total_paid, total_outstanding}.
- [x] Computed from live data (not stored) (FR-9.4 AC-8).
- [x] Optional per-service breakdown.
- [x] Accessible in Admin Portal and Client Portal (scoped) (FR-9.5).

## Notes

Per-service breakdown (get_project_financials_by_service: invoiced/paid/outstanding per service, Custom for unlinked line items) exposed via project overview + UI table; client portal scoped views live. All rollups computed live.

