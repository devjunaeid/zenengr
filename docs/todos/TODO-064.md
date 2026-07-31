---
id: TODO-064
title: Milestone instantiation logic
feature: FEAT-007
story: US-025
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-059]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-064 — Milestone instantiation logic

## Description

When project created with services, instantiate each service's milestone step templates as ProjectMilestone records with Pending status and planned dates.

## Acceptance criteria

- [x] On project creation: for each selected service, copy MilestoneStepTemplate to ProjectMilestone.
- [x] ProjectMilestone model: id, project_id FK, service_id FK, name, sequence_order, status (Pending/InProgress/Completed/Blocked), planned_date, actual_date, assignee_id FK, description, timestamps.
- [x] Instantiated milestones status = Pending (FR-6.4 AC-4).
- [x] Planned dates derived from template expected_duration + project start_date.
- [x] Alembic migration creates project_milestones table.

## Notes

`planned_date = start_date + (prior_days + this_step_duration)` so it marks the END of each step. Edge cases handled: no start_date => null; no duration on template => null. 34 tests green.

