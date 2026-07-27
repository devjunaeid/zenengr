---
id: TODO-122
title: AdminUser model + JWT auth endpoints (login, me)
feature: FEAT-004
story: US-047
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-121, TODO-004]
blocks: [TODO-026, TODO-032, TODO-113]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-122 — AdminUser model + JWT auth endpoints (login, me)

## Description

Create `AdminUser` model with bcrypt-hashed passwords, `POST /api/v1/auth/login` (email + password -> JWT with admin realm scope), and `GET /api/v1/auth/me` (current user from token). Enforce deactivated user rejection and suspended/cancelled tenant rejection at login.

## Acceptance criteria

- [ ] AdminUser model: id, email (unique), hashed_password, display_name, role (Admin/Manager/Employee), status (active/deactivated), tenant_id FK, timestamps.
- [ ] POST /api/v1/auth/login validates credentials, issues JWT with sub, tenant_id, role, realm="admin", exp.
- [ ] GET /api/v1/auth/me returns current user profile (requires Bearer token).
- [ ] Deactivated users get 401 at login.
- [ ] Tenant status Suspended or Cancelled -> 403 at login.
- [ ] Password hashing via passlib bcrypt.
- [ ] JWT secret from settings.
- [ ] Reviewed against `docs/backend-standard.md`.

## Notes

- Auth for Client Portal realm is a separate story (US-xxx).
- Pending completion of TODO-121 (skeleton) and TODO-004 (Tenant model).
