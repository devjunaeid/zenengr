---
id: FEAT-016
title: Custom Roles & Permission Management
status: approved
priority: P0
source: Product decision 2026-08-06
---

# FEAT-016 - Custom Roles & Permission Management

## Goal

Replace the hard-coded role -> permission matrix with a DB-backed role/permission system: a canonical permission catalog lives in code, roles and grants live in the database, tenant admins can create custom roles and toggle permissions for manager/employee/custom roles, and the tenant ADMIN role is a tenant-wide bypass mirroring super_admin within the tenant.

## Functional Requirements

- FR-16.1: Permission catalog in code: canonical (action, resource) list, grouped and labeled, exposed via admin API. Roles and grants live in the database.
- FR-16.2: Roles + grants in DB: `admin_users.role_id` FK added via migration; migration seeds system roles (super_admin/admin/manager/employee) from the current matrix and migrates existing users; `user.role` stays readable as a mapped property/relationship name.
- FR-16.3: Bypass model: super_admin remains a system-wide bypass; tenant ADMIN role is a tenant-wide bypass - always holds every permission within the tenant regardless of toggle state (mirrors super_admin within the tenant). Permission toggles are effective only for manager / employee / custom roles. Admin role: not deletable/renamable; UI shows "Full tenant access" (toggles displayed as always-on/disabled).
- FR-16.4: Enforcement + cache: `has_permission(role, action, resource)` returns True for super_admin and tenant-admin roles, else consults DB grants (cached per role, invalidated on permission change). `require_permission` signature unchanged. Employee owner-only special-cases removed - permission decides access.
- FR-16.5: Admin API: GET /tenant/permissions (catalog), GET /tenant/roles (with permission sets), POST /tenant/roles (custom), PATCH /tenant/roles/{id} (rename + full permission set), DELETE /tenant/roles/{id} (custom only, unassigned, else 409), PATCH /tenant/users/{id}/role (assign role_id), reset-defaults. All audited. super_admin + admin roles protected.
- FR-16.6: Frontend gating: permissions store with `can(action, resource)`; gating sweep replaces role-name checks in staff UI. Roles management UI with toggle switches grouped by resource. Team page role select uses roles API.
- FR-16.7: Migration path: seed system roles from the current matrix, migrate existing users onto role_id, keep `user.role` readable during and after migration.

## Acceptance Criteria

1. GET /tenant/permissions returns the grouped/labeled catalog; catalog source of truth is code.
2. System roles seeded from the current matrix; existing users migrated onto role_id with `user.role` still readable.
3. Tenant admin retains every permission regardless of toggle state; admin role shown as "Full tenant access" (always-on/disabled toggles), not deletable/renamable.
4. has_permission enforces super_admin + tenant-admin bypass, then cached DB grants; cache invalidated on permission change; require_permission signature unchanged.
5. Roles CRUD + assignment API works with guards (custom-only delete, unassigned or 409, admin/super_admin protected) and is fully audited; reset-defaults restores system role sets.
6. Frontend gates via permissions store `can(action, resource)`; role-name checks replaced.
7. Team page role select offers custom roles; last-admin guard preserved.

## Out of Scope (Phase 2)

- Project-scoped grants (team collaboration)
- Client roles
- Role hierarchy
- ABAC (attribute-based access control)

## Dependencies

- FEAT-004 (User & Access Management) - existing RBAC matrix, admin_users, role edit API, last-admin guard

## Decisions

- Permission catalog lives in code (canonical (action, resource) list, grouped/labeled); roles + grants live in the database.
- Tenant ADMIN role = tenant-wide bypass: always has every permission within the tenant regardless of toggle state, mirroring super_admin within the tenant. Toggles effective only for manager / employee / custom roles.
- Admin role: not deletable/renamable; UI shows "Full tenant access" (toggles always-on/disabled).
- Employee owner-only special-cases removed - permission decides access.
- super_admin + admin roles protected from deletion/rename/privilege modification.
