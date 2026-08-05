---
id: TODO-128
title: Upload API
feature: FEAT-012
story: US-049/050
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-125, TODO-127]
blocks: [TODO-129, TODO-130, TODO-131, TODO-136]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-128 — Upload API

## Description

POST multipart upload endpoint with scope selector (USER/TENANT/PROJECT) + folder_id/project_id; 25MB per-file cap; tenant quota check against plan `max_storage_mb`; sha256 computed; file stored via storage backend with tenant-namespaced key; audit logged.

## Acceptance criteria

- [x] POST multipart upload with scope selector + folder_id + project_id (PROJECT scope). (FR-12.3)
- [x] 25MB per-file cap enforced server-side. (FR-12.7)
- [x] Quota check: sum of file_assets sizes + new upload <= plan `max_storage_mb`, else 413. (FR-12.7)
- [x] sha256 computed and stored. (FR-12.3)
- [x] File stored via storage backend with tenant-namespaced key. (FR-12.2)
- [x] Audit on upload. (FR-12.6)

## Notes

- Upload allowed for all staff roles (admin/manager/employee). (FR-12.3)
- PROJECT scope upload restricted to admin/manager. (FR-12.5)
- POST /tenant/files/upload multipart with scope selector; 25MB cap; plan max_storage_mb quota (413); sha256; storage put; audit.
