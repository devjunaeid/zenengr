---
id: TODO-162
title: Permission catalog + DB-backed enforcement + cache
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-161]
blocks: [TODO-163, TODO-164]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-162 - Permission catalog + DB-backed enforcement + cache

## Description

PERMISSION_CATALOG in code (canonical (action, resource) list, grouped/labeled); `has_permission(role, action, resource)` with super_admin + tenant-admin bypass, else DB grants; per-role cache invalidated on permission change; `require_permission` signature unchanged; remove employee owner-only special-cases.

## Acceptance criteria

- [x] PERMISSION_CATALOG defined in code, grouped/labeled. (FR-16.1)
- [x] has_permission: super_admin -> True; tenant-admin role -> True; else DB grants. (FR-16.3, FR-16.4)
- [x] Grants cached per role; cache invalidated on permission change. (FR-16.4)
- [x] require_permission signature unchanged. (FR-16.4)
- [x] Employee owner-only special-cases removed; permission decides access. (FR-16.4)

## Notes

- Tenant ADMIN role = tenant-wide bypass regardless of toggle state. (FR-16.3)
- Shipped: role_has_permission DB grants with super_admin + tenant-admin (admin) bypass; per-role cache invalidated on permission change; require_permission unchanged; employee owner-only special-cases removed - permission decides.
