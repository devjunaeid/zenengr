---
id: TODO-061
title: Instance vs template separation test
feature: FEAT-006
story: US-024
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-059]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-061 — Instance vs template separation test

## Description

Write tests verifying that editing service template after instantiation does NOT change existing project milestones.

## Acceptance criteria

- [x] Test: create service + milestone steps, create project from service, edit template steps, verify project milestones unchanged.
- [x] Test: new projects after template edit get updated template.
- [x] Test: warning flag set correctly for used vs unused templates.

## Notes

TestTemplateSeparation: 4 API-level tests — template rename/reorder/add/remove leave instantiated project milestones untouched; detached service in_use stays false.

