---
id: TODO-072
title: Project overview API (aggregate progress + financial summary)
feature: FEAT-007
story: US-029
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-095]
blocks: [TODO-073, TODO-074]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-072 — Project overview API (aggregate progress + financial summary)

## Description

Build project overview endpoint returning milestone completion percentage and financial summary (total invoiced, total paid, balance due). Computed from live data.

## Acceptance criteria

- [x] GET /api/tenant/projects/{id}/overview returns: milestone_completion_pct, total_invoiced, total_paid, balance_due, linked_invoices[].
- [x] Completion % = (completed milestones / total milestones) * 100.
- [x] Financial numbers computed from TODO-095 service.
- [x] Linked invoices list with status.

## Notes

Financial fields + linked_invoices now computed from live invoice/transaction data (TODO-095 wired); overview endpoint complete.

