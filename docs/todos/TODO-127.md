---
id: TODO-127
title: Folders API
feature: FEAT-012
story: US-049
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-125]
blocks: [TODO-128]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-127 — Folders API

## Description

Folders API for the tenant gallery: GET nested folder tree, POST create folder (scope + optional project_id), PATCH rename, DELETE empty-only. Scope/project rules + tenant isolation on every query.

## Acceptance criteria

- [x] GET folder tree endpoint per tenant (nested, any depth). (FR-12.4)
- [x] POST creates folder with scope + optional project_id; nesting restricted within the same scope. (FR-12.4)
- [x] PATCH renames folder; unique sibling names enforced per parent. (FR-12.4)
- [x] DELETE removes folder only if empty. (FR-12.4)
- [x] Tenant isolation on every query; cross-tenant access returns 404. (FR-12.2, FR-12.5)

## Notes

- Auto root folder provisioning is TODO-137, not this task.
- Empty-only delete prevents orphaned child folders.
- Folder CRUD + recursive tree; virtual My files root; scope-locked nesting; per-project subfolders; constraint fix migration d4e5f6a7b8c9.
