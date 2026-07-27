---
id: TODO-064
title: Milestone instantiation logic
feature: FEAT-007
story: US-025
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-059]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-064 — Milestone instantiation logic

## Description

When project created with services, instantiate each service's milestone step templates as ProjectMilestone records with Pending status and planned dates.

## Acceptance criteria

- [ ] On project creation: for each selected service, copy MilestoneStepTemplate to ProjectMilestone.
- [ ] ProjectMilestone model: id, project_id FK, service_id FK, name, sequence_order, status (Pending/InProgress/Completed/Blocked), planned_date, actual_date, assignee_id FK, description, timestamps.
- [ ] Instantiated milestones status = Pending (FR-6.4 AC-4).
- [ ] Planned dates derived from template expected_duration + project start_date.
- [ ] Alembic migration creates project_milestones table.

## Notes

