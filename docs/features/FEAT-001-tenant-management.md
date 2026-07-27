---
id: FEAT-001
title: Tenant Management
status: approved
priority: P0
source: docs/prd.md §6.1
---

# FEAT-001 — Tenant Management

## Goal

Provide Super Admin with full lifecycle management for tenants — create, view, edit, suspend, and deactivate. Enforce strict data isolation between tenants and prevent Super Admin from accessing tenant operational data.

## Scope

### In Scope
- Super Admin tenant CRUD (create, view, edit, suspend, deactivate)
- Tenant unique identifier/slug for subdomain or login routing
- Tenant lifecycle status: Trial, Active, Suspended, Cancelled
- Full data isolation between tenants (clients, projects, invoices, users)
- Tenant Admin self-service view/edit of tenant profile (name, logo, contact, branding)

### Out of Scope
- Super Admin access to tenant operational data (clients, projects, invoices) — strictly container-level only
- Super Admin impersonation of tenant users (Phase 2 candidate)
- Automated tenant provisioning via self-service signup (Phase 2 candidate)

## Functional Requirements

- FR-1.1: Super Admin can create, view, edit, suspend, and delete/deactivate tenants.
- FR-1.2: Each tenant has a unique identifier/slug (used for subdomain or login routing, e.g. `tenantname.platform.com` — optional for MVP, but data model should support it).
- FR-1.3: Tenant has a lifecycle status: `Trial`, `Active`, `Suspended`, `Cancelled`.
- FR-1.4: A tenant's data (clients, projects, invoices, users) is fully isolated from other tenants — no cross-tenant visibility under any tenant-side role.
- FR-1.5: Tenant Admin can view/edit their own tenant's profile info (business name, logo, contact info, branding) but cannot change subscription tier or platform-level feature flags.

## Acceptance Criteria

1. Super Admin can create a tenant with name, slug, and initial status.
2. Super Admin can view a list of all tenants with status and key metadata.
3. Super Admin can edit a tenant's profile fields.
4. Super Admin can suspend a tenant; suspended tenants' users lose portal access.
5. Super Admin can deactivate/delete a tenant; deactivated tenant data is preserved but inaccessible.
6. A tenant Admin can view and edit their own tenant's profile (business name, logo, contact info) but NOT subscription or feature flags.
7. No tenant-side query across any core entity (client, project, invoice) returns data from another tenant.
8. Super Admin attempting to access any tenant-scoped operational endpoint receives a denial.

## Dependencies

- FEAT-002 (Subscription & Settings) — tenant status feeds into subscription lifecycle
- FEAT-003 (Feature Flags) — tenant-level feature flag queries depend on tenant existence

## Decisions

- **Super Admin is strictly container-level:** NO access to tenant operational data (clients, projects, invoices), no support impersonation in MVP.
