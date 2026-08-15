---
id: FEAT-004
title: User & Access Management
status: approved
priority: P0
source: docs/prd.md §6.4
---

# FEAT-004 — User & Access Management

## Goal

Provide tenant-level user administration with role-based access control for both admin-side staff (Admin, Manager, Employee) and client-side users (Client Portal). Enforce two separate auth realms with distinct login portals and session scopes.

## Scope

### In Scope
- Admin user invite, create, edit, deactivate/reactivate with roles: Admin, Manager, Employee
- Role-based permission matrix per FR-4.2
- Separate Admin/Ops Portal and Client Portal login
- Soft-delete/deactivate for admin users (preserve historical attribution)
- Invite flow with role pre-assignment and expiry
- Role changes take effect on next request
- Admin password reset on behalf of another user
- Audit trail for sensitive admin actions (role changes, deactivations, invoice issuance, payment recording)
- Protection against removing last remaining Admin
- Client User management per Client (invite, deactivate, portal access)
- Client Portal scoped to own Client's projects, invoices, transactions, comments

### Out of Scope
- Self-service signup / registration (admin users created only by Tenant Admin)
- Social login / OAuth (Phase 2 candidate)
- SAML/SSO (Phase 2 candidate)
- Granular custom roles beyond Admin/Manager/Employee (Phase 2 candidate)

## Functional Requirements

- FR-4.1: Tenant Admin can invite/create users with roles: `Admin`, `Manager`, `Employee`.
- FR-4.2: Role-based permission matrix (minimum for MVP):

| Capability | Admin | Manager | Employee |
|---|---|---|---|
| Manage tenant settings | ✅ | ❌ | ❌ |
| Manage admin users/roles | ✅ | ❌ | ❌ |
| Manage clients | ✅ | ✅ | View only |
| Manage services catalog | ✅ | ✅ | View only |
| Create/manage projects | ✅ | ✅ | Assigned only |
| Update milestone status | ✅ | ✅ | Assigned only |
| Create/manage invoices | ✅ | ✅ | ❌ |
| Record payments | ✅ | ✅ | ❌ |
| View financial reports | ✅ | ✅ | ❌ |
| Post/view comments | ✅ | ✅ | Assigned only |
| Edit own profile/password | ✅ | ✅ | ✅ |
| Invite/deactivate other admin users | ✅ | ❌ | ❌ |

- FR-4.3: Admin users log in via the **Admin/Ops Portal**, distinct URL/UI from the client portal.
- FR-4.4: Deactivating an admin user must not delete their historical activity (comments, actions) — soft-delete/deactivate only.
- FR-4.9: Tenant Admin can **invite** a new admin user via email; invite flow includes role pre-assignment and expires after a defined period if unaccepted.
- FR-4.10: Tenant Admin can **edit** an existing admin user's role/permissions at any time; role changes take effect on next request (no need to re-login, ideally).
- FR-4.11: Tenant Admin can **deactivate/reactivate** an admin user. A deactivated user immediately loses portal access but their historical records remain intact and attributed to them.
- FR-4.12: Tenant Admin can trigger a **password reset** on behalf of another admin user (support scenario), separate from that user's own self-service reset (see 6.11).
- FR-4.13: System maintains a basic **audit trail** of sensitive admin actions (role changes, deactivations, invoice issuance, payment recording) — who did what and when. A simple activity log list is sufficient for MVP.
- FR-4.14: A user cannot deactivate or edit the role of the tenant's last remaining Admin.
- FR-4.5: A Client (company/contact record) can have one or more Client Users associated with it.
- FR-4.6: Client Users log in via a separate **Client Portal**, seeing only their own Client's projects, invoices, transactions, and comments.
- FR-4.7: Tenant Admin/Manager can invite a Client User (e.g., via email invite) and optionally deactivate access.
- FR-4.8: Client Users cannot see other clients' data, other tenants, or internal-only comments (see 6.10).

## Acceptance Criteria

1. Tenant Admin can invite an admin user via email with role assignment; invite link expires after N days.
2. Invited user completes registration and logs into the Admin/Ops Portal with correct role permissions.
3. Tenant Admin can edit a user's role; permission change takes effect on next API request.
4. Tenant Admin can deactivate a user; deactivated user cannot log in; their historical comments/actions remain attributed.
5. Tenant Admin cannot deactivate or change role of the last remaining Admin.
6. A Manager user can create projects and clients but cannot manage admin users or tenant settings.
7. An Employee user sees only assigned projects; cannot create invoices or record payments.
8. Tenant Admin/Manager can invite a Client User; Client User logs into separate Client Portal scoped to their own Client only.
9. Client User cannot see other clients' data, other tenants, or internal-only comments.

## Dependencies

- FEAT-001 (Tenant Management) — tenant must exist for users to belong to
- FEAT-005 (Client Management) — Client Users depend on Client records
- FEAT-011 (Profile Self-Service) — shared profile management capabilities

## Decisions

- **Two separate auth realms:** Admin/Ops Portal (Super Admin, Admin, Manager, Employee) and Client Portal (Client Users).
- **One Client User login = exactly one tenant relationship.**
- **FR-4.2 role matrix must be implemented verbatim** as the authorization backbone.

## Notes

- Client User onboarding reworked: Tenant Admin/Manager creates a Client WITH `client_user_email` + password, making that user the primary billing contact (active by default). Admin can change the Client User's password and revoke/restore portal access. Invite-based Client User onboarding removed from UI; invite endpoints dormant.
