---
id: TODO-062
title: Project model + create API
feature: FEAT-007
story: US-025
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004, TODO-043, TODO-056]
blocks: [TODO-063, TODO-064, TODO-065, TODO-068, TODO-070, TODO-072, TODO-075, TODO-100]
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-062 — Project model + create API

## Description

Create Project model (tenant_id, name, client_id, status, start_date, owner_id) with create API. Service selection at creation triggers milestone instantiation.

## Acceptance criteria

- [x] Project model: id, tenant_id FK, name, client_id FK, status enum (Draft/Active/OnHold/Completed/Cancelled), start_date, owner_id FK, timestamps.
- [x] Alembic migration creates projects table.
- [x] POST /api/tenant/projects with services[] array.
- [x] ProjectService join model: project_id + service_id + status (Active/Cancelled).
- [x] Project status defaults to Draft on creation (FR-7.2).
- [x] Tenant Admin/Manager can create. Employee view-only on assigned projects.

## Notes

Implemented in `app/models/project.py` + `app/models/project_service.py` + `app/repositories/projects.py` + `app/services/projects.py` + `app/api/v1/projects.py` + migration `c1d2e3f4a5b6`. 34 tests green in `tests/test_projects_api.py`.

