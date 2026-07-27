---
id: TODO-063
title: Service selection UI at project creation
feature: FEAT-007
story: US-025
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-063 — Service selection UI at project creation

## Description

Build project creation form with multi-select service picker. Selected services show milestone preview before submission.

## Acceptance criteria

- [ ] Service picker component fetches catalog (GET /api/tenant/services).
- [ ] Multi-select with checkboxes or multiselect dropdown.
- [ ] Preview of milestone steps for selected services shown.
- [ ] On submit, project created + milestones instantiated (TODO-064).

## Notes

