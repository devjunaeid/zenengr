---
id: TODO-068
title: Add service to project API
feature: FEAT-007
story: US-027
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-056]
blocks: [TODO-069]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-068 — Add service to project API

## Description

Build POST endpoint to add a service to an existing active project. New milestones instantiate for added service only. Existing milestones unchanged.

## Acceptance criteria

- [ ] POST /api/tenant/projects/{id}/services adds service + instantiates milestones (FR-7.4).
- [ ] New service milestones start at Pending (FR-6.4).
- [ ] Existing services and milestones unchanged (FR-7.4).
- [ ] Only works on Active projects.
- [ ] New service billed via new invoice (FR-7.6, FR-8.4).

## Notes

