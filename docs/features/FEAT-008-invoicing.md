---
id: FEAT-008
title: Invoicing
status: approved
priority: P0
source: docs/prd.md §6.8
---

# FEAT-008 — Invoicing

## Goal

Let tenant staff generate invoices for projects with line items linked to project services. Invoices progress through a lifecycle from Draft (editable) to Issued (immutable) through payment statuses. A project can have multiple invoices over its lifetime. Client Portal shows invoice status and balance due.

## Scope

### In Scope
- Invoice generation for a project, selecting project services / line items
- Invoice fields: number (tenant-scoped sequential), issue date, due date, line items, subtotal, optional tax, total, status
- Invoice status lifecycle: Draft → Issued/Sent → Partially Paid → Paid → (Overdue, Void/Cancelled)
- Draft invoices fully editable; Issued invoices locked/immutable
- Multiple invoices per project (1-to-many)
- Client Portal invoice view with status and balance due
- PDF export/view of invoices

### Out of Scope
- Milestone-triggered auto-invoicing (Phase 2, per PRD §7)
- Recurring/subscription billing to clients (Phase 2, per §3.2)
- Credit notes / adjustment invoices (Phase 2 candidate; corrections via new invoice in MVP)
- Tax engine / multi-currency (Phase 2, per §3.2)

## Functional Requirements

- FR-8.1: Tenant Admin/Manager can generate an Invoice for a Project, selecting which Project Service(s) / line items to include.
- FR-8.2: Invoice must contain: invoice number (tenant-scoped sequential numbering, per FR-2.4 settings), issue date, due date, line items (each linked to a Project Service or a custom line item), subtotal, tax (optional MVP), total, and status.
- FR-8.3: Invoice status lifecycle: `Draft` → `Issued/Sent` → `Partially Paid` → `Paid` → (or `Overdue`, `Void`/`Cancelled`).
- FR-8.4: **Draft invoices are editable**; once **Issued**, core financial fields become **locked/immutable**. Corrections via a new adjustment (credit note or new invoice), never by editing history.
- FR-8.5: A Project can have **multiple invoices** over its lifetime.
- FR-8.6: Client Portal shows all invoices for their own projects with current status and balance due.
- FR-8.7: Invoices should be exportable/viewable as PDF.

## Acceptance Criteria

1. Tenant Admin/Manager can create a Draft invoice for a project, selecting line items from project services.
2. Draft invoice fields (line items, amounts, dates) are editable.
3. Issuing an invoice locks all core financial fields; no further edits allowed.
4. Issued invoice cannot be deleted; can only be Void/Cancelled.
5. A project can have multiple invoices; each invoice tracks its own status independently.
6. Client Portal shows invoices for the client's projects with status, amount, and balance due.
7. Invoice can be exported as PDF with correct layout and data.
8. Invoice number follows tenant-scoped sequential format configured in tenant settings.

## Dependencies

- FEAT-002 (Subscription & Settings) — invoice numbering format from tenant settings
- FEAT-007 (Project Management) — invoices are linked to projects
- FEAT-006 (Service Catalog & Milestones) — line items reference project services
- FEAT-009 (Payments) — payments update invoice status

## Decisions

- **Immutable once Issued** per FR-8.4. Draft editable.
- **Project-to-Invoice is 1-to-many.**
- **Manual invoicing only** — no milestone-triggered auto-invoicing in MVP (Phase 2).
