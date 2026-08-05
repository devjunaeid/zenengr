---
id: TODO-125
title: FileFolder + FileAsset models + migration
feature: FEAT-012
story: US-049
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-123]
blocks: [TODO-126, TODO-127, TODO-128, TODO-137]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-125 — FileFolder + FileAsset models + migration

## Description

Create `FileFolder` and `FileAsset` models + migration: folder tree (self-referential parent, any depth), scope enum (USER/TENANT/PROJECT), `project_id` for PROJECT scope, unique `storage_key`, `size_bytes`, `sha256`, `content_type`, name, polymorphic creator. Tenant isolation on all queries.

## Acceptance criteria

- [x] FileFolder model: id, tenant_id FK, parent_id (nullable, self-referential), scope enum, project_id (nullable), name, created_at; unique sibling names per parent. (FR-12.4)
- [x] FileAsset model: id, tenant_id FK, folder_id FK, scope enum, project_id (nullable), name, storage_key (unique), size_bytes, content_type, sha256, creator_id + creator_type (polymorphic), timestamps. (FR-12.3)
- [x] Scope enum `FileScope`: user / tenant / project. (FR-12.3)
- [x] Alembic migration creates both tables with indexes (tenant_id, folder_id, scope, project_id, storage_key unique). (FR-12.2)
- [x] All queries tenant-isolated. (FR-12.2)

## Notes

- Modeled after existing model conventions (comment.py polymorphic author pattern).
- FileFolder (tree, scope, project_id) + FileAsset (storage_key unique, sha256, size, creator polymorphic) + filescope enum + migration c3d4e5f6a7b8.
