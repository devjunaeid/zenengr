---
id: TODO-063
title: Service selection UI at project creation
feature: FEAT-007
story: US-025
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-063 — Service selection UI at project creation

## Description

Build project creation form with multi-select service picker. Selected services show milestone preview before submission.

## Acceptance criteria

- [x] Service picker component fetches catalog (GET /api/tenant/services).
- [x] Multi-select with checkboxes or multiselect dropdown.
- [x] Preview of milestone steps for selected services shown.
- [x] On submit, project created + milestones instantiated (TODO-064).

## Notes

