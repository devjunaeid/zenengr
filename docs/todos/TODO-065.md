---
id: TODO-065
title: Milestone update API
feature: FEAT-007
story: US-026
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062]
blocks: [TODO-066, TODO-067]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-065 — Milestone update API

## Description

Build PATCH endpoint for milestone fields: status (4-state enum), planned/target date, actual completion date, assignee. Status changes can be non-sequential (FR-6.4 AC-7).

## Acceptance criteria

- [ ] PATCH /api/tenant/projects/{id}/milestones/{milestone_id} updates: status, planned_date, actual_date, assignee_id.
- [ ] Status values: Pending, In Progress, Completed, Blocked.
- [ ] Status change in any order allowed (US-026 AC2).
- [ ] Employee can only update milestones on assigned projects (FR-4.2, FR-6.6).
- [ ] Milestone status changes visible on Client Portal (TODO-074).

## Notes

