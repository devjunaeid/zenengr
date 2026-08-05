---
id: TODO-129
title: File list/metadata API
feature: FEAT-012
story: US-050
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-128]
blocks: [TODO-131, TODO-134]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-129 — File list/metadata API

## Description

Scoped file listing by folder/scope/project with pagination + metadata (name, size, type, scope, uploader, created). Visibility filtering enforced server-side (USER = uploader only, TENANT = all staff, PROJECT = staff with project access).

## Acceptance criteria

- [x] GET file list endpoint with pagination + metadata (name, size, type, scope, uploader, created). (FR-12.3)
- [x] Filters: folder_id, scope, project_id. (FR-12.3)
- [x] USER scope filtered to uploader; TENANT to all staff; PROJECT to staff with project access. (FR-12.5)
- [x] Cross-tenant/cross-client access returns 404. (FR-12.5)
- [x] Visibility filtering server-side only (never rely on client). (FR-12.5)

## Notes

- Excludes storage_key/content bytes from list payloads.
- GET /tenant/files with folder/scope/project filters + pagination + q; USER scope creator-only; TENANT/PROJECT all staff.
