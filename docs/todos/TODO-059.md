---
id: TODO-059
title: Template snapshot logic on project attachment
feature: FEAT-006
story: US-024
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-056, TODO-062]
blocks: [TODO-061]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-059 — Template snapshot logic on project attachment

## Description

When a service is attached to a project, instantiate milestone step templates as concrete ProjectMilestone records (copies). Subsequent template edits do not mutate existing project milestones (FR-6.5).

## Acceptance criteria

- [ ] On project creation/service attachment: copy each MilestoneStepTemplate to a new ProjectMilestone.
- [ ] ProjectMilestone stores: name, sequence_order, expected_duration_days, description, status (Pending).
- [ ] No reference back to MilestoneStepTemplate after instantiation (immutable copy).
- [ ] Editing service template after instantiation leaves existing milestones unchanged (FR-6.5).
- [ ] Warning shown when editing template with existing instantiations (TODO-060).

## Notes

