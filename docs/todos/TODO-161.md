---
id: TODO-161
title: Role + RolePermission models + migration
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-162]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-161 - Role + RolePermission models + migration

## Description

Role and RolePermission models; `admin_users.role_id` FK migration; seed system roles (super_admin/admin/manager/employee) from the current permission matrix; migrate existing users onto role_id; keep `user.role` readable (mapped property/relationship name) for back-compat.

## Acceptance criteria

- [x] Role + RolePermission models with tenant scoping (system roles + tenant custom roles). (FR-16.2)
- [x] `admin_users.role_id` FK migration; existing users migrated. (FR-16.7)
- [x] System roles seeded from the current matrix. (FR-16.2)
- [x] `user.role` stays readable as mapped property/relationship name. (FR-16.7)

## Notes

- Roles in DB; permission catalog stays in code (FR-16.1).
- Admin role flagged as protected/not deletable/not renamable. (FR-16.3)
- Shipped: Role + RolePermission models; admin_users.role_id FK migration e1f2a3b4c5d6; system roles seeded (admin 14 / manager 12 / employee 7 perms + roles resource, migration f2a3b4c5d6e7); user.role stays readable.
