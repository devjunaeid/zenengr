---
id: FEAT-005
title: Client Management
status: approved
priority: P0
source: docs/prd.md §6.5
---

# FEAT-005 — Client Management

## Goal

Let tenant staff manage their clients (companies/individuals) with contact details, billing info, status tracking, notes, tags, and activity history. Provide search/filter capabilities and archival that preserves historical financial records.

## Scope

### In Scope
- Client CRUD (create, edit, view) with contact details, billing info, status (Active, Archived)
- Multiple Client Users per Client with single primary billing contact
- Client list with summary rollups (active projects, total invoiced, outstanding balance)
- Internal-only notes and tags/labels per Client
- Automatic activity/interaction history per Client
- Search and filter client list (name, status, tag, outstanding balance)
- Archiving: hides from active lists, preserves projects/invoices, revokes Client Portal access
- Client Portal limited self-service: Client Users can update contact details (not billing-sensitive fields)

### Out of Scope
- Client-side self-service for billing-sensitive fields (tax ID, billing address) — requires Tenant Admin/Manager edit
- Bulk import/export of clients (Phase 2 candidate)
- Client portal registration without invite (Phase 2 candidate)

## Functional Requirements

- FR-5.1: Tenant Admin/Manager can create, edit, and view Clients (company or individual) within their tenant.
- FR-5.2: A Client record holds contact details, billing info (billing address, tax ID if applicable), and status (`Active`, `Archived`).
- FR-5.3: A Client can have multiple Client Users (contacts) but a single primary billing contact.
- FR-5.4: Client list should show summary rollups: number of active projects, total invoiced, total outstanding balance.
- FR-5.5: Tenant Admin/Manager can add free-text **notes** and simple **tags/labels** to a Client record — notes are internal-only, never visible on the Client Portal.
- FR-5.6: System maintains a basic **activity/interaction history** per Client — automatically logged events such as project created, invoice issued, payment received, comment posted.
- FR-5.7: Tenant Admin/Manager can **search and filter** the client list (by name, status, tag, outstanding balance).
- FR-5.8: Archiving a Client hides them from default active lists but preserves all historical projects/invoices; archived clients' users lose Client Portal access.
- FR-5.9: Client Users can view and update limited fields on their own Client profile (e.g., contact details) from the Client Portal — billing-sensitive fields (tax ID, billing address) require Tenant Admin/Manager edit rather than direct self-service.

## Acceptance Criteria

1. Tenant Admin/Manager can create a Client with name, contact info, billing address, and initial status.
2. Client list shows rollup columns: active project count, total invoiced, outstanding balance.
3. Tenant staff can add internal notes and tags to a Client; notes are invisible in Client Portal.
4. Activity history auto-logs project creation, invoice issuance, payment, and comment events.
5. Search by name, status, tag, and outstanding balance range returns correct results.
6. Archiving a Client removes them from active list; historical projects/invoices remain intact.
7. Archived Client's users cannot log into Client Portal.
8. Client User can update their own contact details (phone, email) but NOT tax ID or billing address from Client Portal.

## Dependencies

- FEAT-001 (Tenant Management) — clients are tenant-scoped
- FEAT-004 (User & Access Management) — Client Users are associated with Clients
- FEAT-007 (Project Management) — project rollups feed client summary
- FEAT-008 (Invoicing) — financial rollups feed client summary

## Decisions

- None beyond PRD.

## Notes

- Client User onboarding: client creation now includes `client_user_email` + password for the primary billing contact (active by default); admin password change + revoke/restore replace the invite flow; invite UI removed.
