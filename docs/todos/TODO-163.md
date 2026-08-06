---
id: TODO-163
title: Roles CRUD + assignment API
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-162]
blocks: [TODO-165, TODO-166]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-163 - Roles CRUD + assignment API

## Description

GET /tenant/permissions (catalog), GET /tenant/roles (with permission sets), POST /tenant/roles (custom), PATCH /tenant/roles/{id} (rename + full permission set), DELETE /tenant/roles/{id} (custom only, unassigned, else 409), PATCH /tenant/users/{id}/role (assign role_id), reset-defaults. All audited; super_admin + admin roles protected.

## Acceptance criteria

- [x] GET /tenant/permissions returns grouped/labeled catalog. (FR-16.5)
- [x] GET/POST/PATCH/DELETE /tenant/roles with permission sets; DELETE custom only, unassigned, else 409. (FR-16.5)
- [x] PATCH /tenant/users/{id}/role assigns role_id; last-admin guard preserved. (FR-16.5)
- [x] Reset-defaults restores system role sets. (FR-16.5)
- [x] All actions audited; super_admin + admin roles protected from delete/rename/privilege modification. (FR-16.5)

## Notes

- Admin role: not deletable/renamable; toggles always-on/disabled in UI. (FR-16.3)
- Shipped: GET catalog/permissions; roles CRUD (admin immutable full-access, super_admin protected, custom-only delete + assigned-409); reset-defaults; PATCH user role (role_id + enum sync + last-admin guard); all audited.
