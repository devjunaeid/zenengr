---
id: TODO-072
title: Project overview API (aggregate progress + financial summary)
feature: FEAT-007
story: US-029
status: proposed
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

- [ ] GET /api/tenant/projects/{id}/overview returns: milestone_completion_pct, total_invoiced, total_paid, balance_due, linked_invoices[].
- [ ] Completion % = (completed milestones / total milestones) * 100.
- [ ] Financial numbers computed from TODO-095 service.
- [ ] Linked invoices list with status.

## Notes

