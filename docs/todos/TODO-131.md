---
id: TODO-131
title: Delete/rename/move API + RBAC
feature: FEAT-012
story: US-050
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-129]
blocks: [TODO-134]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-131 — Delete/rename/move API + RBAC

## Description

File management endpoints: DELETE (storage + row), PATCH rename, move between folders (same scope restriction). Permission rules per scope; permission matrix entries `view/files` + `manage/files`.

## Acceptance criteria

- [x] DELETE removes file from storage + row. (FR-12.5)
- [x] PATCH rename file. (FR-12.4)
- [x] Move file between folders; nesting/move restricted within the same scope. (FR-12.4)
- [x] USER scope: creator only (delete/rename). (FR-12.5)
- [x] TENANT scope: admin/manager delete/rename/move; staff view only. (FR-12.5)
- [x] PROJECT scope: admin/manager delete/rename/move; staff view only. (FR-12.5)
- [x] Permission matrix entries: `view/files`, `manage/files`. (FR-4.2)
- [x] Unauthorized access returns 404. (FR-12.5)

## Notes

- Delete must remove the object from the storage backend and the row.
- USER creator-only; TENANT/PROJECT admin/manager; files resource added to permission matrix (view all staff, manage admin+manager); 404 on unauthorized.
