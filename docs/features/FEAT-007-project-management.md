---
id: FEAT-007
title: Project Management
status: approved
priority: P0
source: docs/prd.md §6.7
---

# FEAT-007 — Project Management

## Goal

Let tenant staff create projects for clients by selecting one or more services, tracking milestone progress, and managing scope changes via mid-project service additions. Project overview shows aggregate progress and financial summary across all linked invoices.

## Scope

### In Scope
- Project creation with name, client, start date, status (Draft, Active, On Hold, Completed, Cancelled), owner
- Attachment of one or more services, each instantiated as a Project Service with milestones
- Mid-project service additions (scope growth) with billing implications via new invoice
- Project overview: aggregate milestone progress, financial summary (invoiced, paid, balance), linked invoices
- Soft removal of services (mark Cancelled, not deleted) when invoicing has occurred

### Out of Scope
- Milestone-triggered auto-invoicing (Phase 2, per PRD §7)
- Gantt charts / timeline visualization (Phase 2 candidate)
- Resource allocation / workload management (Phase 2 candidate)
- Client-side project creation (tenant staff only)

## Functional Requirements

- FR-7.1: Tenant Admin/Manager can create a Project for a specific Client, selecting one or more Services to include.
- FR-7.2: A Project must capture: name, associated Client, start date, status (`Draft`, `Active`, `On Hold`, `Completed`, `Cancelled`), and owner (assigned admin user).
- FR-7.3: Each Service attached to a Project becomes a **Project Service** instance, carrying its own instantiated milestones (per 6.6).
- FR-7.4: A Project must support adding **additional Services after creation** (mid-life scope growth) — see PRD §7 for billing implications.
- FR-7.5: Project overview screen (both Admin and Client Portal, scoped appropriately) must show: overall progress (aggregate of milestone completion), financial summary (total invoiced, total paid, balance due), and linked invoices.
- FR-7.6: Removing a Service from a Project after invoicing has occurred should be restricted/soft (mark as `Cancelled` rather than deleted) to preserve financial history integrity.

## Acceptance Criteria

1. Tenant Admin/Manager can create a project with a client, one or more services, start date, and owner.
2. Each service attached to the project instantiates milestones per the service template.
3. Project overview shows aggregate milestone completion percentage.
4. Project overview shows total invoiced, total paid, and balance due derived from linked invoices.
5. Tenant staff can add a new service to an active project; milestones instantiate for the new service.
6. Removing a service that has invoices referencing it marks it as Cancelled (not deleted).
7. Removing a service with no invoices deletes it and its milestones.
8. Client Portal shows project overview with progress and financial summary scoped to that client.

## Dependencies

- FEAT-001 (Tenant Management) — projects are tenant-scoped
- FEAT-005 (Client Management) — projects belong to clients
- FEAT-006 (Service Catalog & Milestones) — services and milestone templates feed project instantiation
- FEAT-008 (Invoicing) — financial rollups depend on linked invoices

## Decisions

- **Mid-project service additions supported** per PRD §7: never reopen issued invoices; new scope bills via new invoice.
