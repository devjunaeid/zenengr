---
id: TODO-134
title: File explorer UI (Admin Portal)
feature: FEAT-012
story: US-049/050
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-127, TODO-128, TODO-129, TODO-130, TODO-131]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-134 — File explorer UI (Admin Portal)

## Description

`/app/files` page: folder tree + breadcrumbs, upload dialog with visibility scope selector (USER/TENANT/PROJECT) + folder/project picker, file table (name, size, type, scope, uploader, created), download/rename/delete/move actions respecting server-side permissions, quota error states.

## Acceptance criteria

- [x] `/app/files` page with folder tree + breadcrumbs. (FR-12.4)
- [x] Upload dialog with visibility scope selector + folder/project picker. (FR-12.3)
- [x] File table: name, size, type, scope, uploader, created. (FR-12.3)
- [x] Download/rename/delete/move actions respect server-side permissions (hide unavailable actions). (FR-12.5)
- [x] Error states for quota exceeded (413). (FR-12.7)

## Notes

- Follows `docs/frontend-standard.md` + `docs/ui-ux-spec.md`.
- File explorer UI at /app/files: folder tree, upload dialog with scope selector, file table, permission-aware actions, quota error states.