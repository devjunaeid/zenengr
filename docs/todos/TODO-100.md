---
id: TODO-100
title: Comment model + post API
feature: FEAT-010
story: US-039
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-004]
blocks: [TODO-101, TODO-102, TODO-103, TODO-106]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-100 — Comment model + post API

## Description

Create Comment model (project_id, author_id, author_type, content, is_internal) + POST API for project-level comments. MVP: project-level only (not milestone-level).

## Acceptance criteria

- [ ] Comment model: id, project_id FK, author_id, author_type enum (tenant_admin/tenant_manager/tenant_employee/client_user), content text, is_internal bool, created_at, timestamps.
- [ ] Alembic migration creates comments table.
- [ ] POST /api/tenant/projects/{id}/comments posts comment.
- [ ] POST /api/client/projects/{id}/comments posts comment (Client Portal).
- [ ] Tenant staff and Client Users can post (FR-10.1).
- [ ] MVP scope: project-level threads only (FR-10.4).

## Notes

