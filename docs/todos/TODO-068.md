---
id: TODO-068
title: Add service to project API
feature: FEAT-007
story: US-027
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-056]
blocks: [TODO-069]
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-068 — Add service to project API

## Description

Build POST endpoint to add a service to an existing active project. New milestones instantiate for added service only. Existing milestones unchanged.

## Acceptance criteria

- [x] POST /api/tenant/projects/{id}/services adds service + instantiates milestones (FR-7.4).
- [x] New service milestones start at Pending (FR-6.4).
- [x] Existing services and milestones unchanged (FR-7.4).
- [x] Only works on Active projects.
- [ ] New service billed via new invoice (FR-7.6, FR-8.4).

## Notes

409 if project not Active; 409 if service already attached; 404 if service not in tenant. 34 tests green.

