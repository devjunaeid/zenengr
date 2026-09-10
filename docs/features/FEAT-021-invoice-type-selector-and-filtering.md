---
id: FEAT-021
title: Invoice Type Selector, Billed-To Info & Advanced Filtering
status: approved
priority: P1
source: User requirement 2026-09-09
---

# FEAT-021 — Invoice Type Selector, Billed-To Info & Advanced Filtering

## Goal

Provide a streamlined, intuitive invoice creation workflow with an explicit Type Selector between **General Invoice** and **Project Invoice**. For General Invoices, allow staff to input recipient / client **Billed To** information (name, email, phone, address, tax ID). For Project Invoices, provide a searchable, real-time filtered Project Picker. Enhance the Invoices List page with multi-dimensional filtering by invoice type (All, Project, General) and an optional date range filter (From Date, To Date).

## Scope

### In Scope

- **Invoice Creation Type Selector**: Dedicated toggle/segmented control to choose between "Project Invoice" and "General Invoice".
- **General Invoice Billed-To Information**:
  - Ability to record Billed-To details on General Invoices (`name`, `email`, `phone`, `address`, `tax_id`).
  - Stored in `invoices.billed_to` JSONB column.
  - Option to quickly pick an existing Client to pre-fill Billed-To fields, or type custom info directly.
  - Rendered in invoice detail view (`/app/invoices/[id]`), invoice edit view, and invoice PDF (`/tenant/invoices/{id}/pdf`).
- **Project Invoice Searchable Picker**:
  - Real-time search/filter input to quickly find and select a project by name or client name.
  - Clear visual indicator of the currently selected project and quick switch/clear option.
- **Invoice List Filtering**:
  - Filter by Invoice Type: All, Project Invoice (`project_id IS NOT NULL`), General Invoice (`project_id IS NULL`).
  - Filter by Date with optional Date Range (`date_from` and `date_to`).
  - Responsive filter bar with quick Reset/Clear filters action.
  - Table and mobile card views display Billed-To recipient for General Invoices.

### Out of Scope

- Client Portal self-service invoice generation (staff-only).
- Multi-currency rate conversions (handled per tenant currency setting).

## Functional Requirements

- **FR-21.1**: New Invoice Create view displays a clear type selector: "Project Invoice" vs "General Invoice".
- **FR-21.2**: When "General Invoice" is selected:
  - Form displays Billed-To info inputs: Name (required/primary), Email, Phone, Address, Tax ID / VAT.
  - Form offers an optional quick-fill from existing tenant clients.
  - Project selection is omitted/cleared; line items default to custom entries.
- **FR-21.3**: When "Project Invoice" is selected:
  - Form displays an interactive, searchable Project Picker with real-time text query filtering across project and client names.
  - Selecting a project automatically fetches active project services and ledger discount rules.
- **FR-21.4**: `Invoice` entity supports a `billed_to` JSONB field in database, Pydantic schemas, and API responses.
- **FR-21.5**: Invoice detail view and PDF generator render the `billed_to` information when present for general invoices.
- **FR-21.6**: Invoice listing API `GET /tenant/invoices` and frontend list view support `invoice_type` (`all`, `project`, `general`), `date_from`, and `date_to` parameters.

## Acceptance Criteria

1. Navigating to `/app/invoices/new` presents an invoice type selector: Project Invoice vs General Invoice.
2. Selecting General Invoice shows Billed To fields (Name, Email, Phone, Address, Tax ID); submitting saves `billed_to` and creates the invoice without a project link.
3. Selecting Project Invoice displays a searchable project combobox/picker; typing filters projects instantly; selecting one loads its services.
4. Viewing or generating PDF for a General Invoice displays the Billed To details in the header Billed To section.
5. Invoices list page allows filtering by Type (All / Project / General) and optional Date Range (From / To).
6. Filtering by date range correctly filters invoices matching the date criteria.

## Dependencies

- FEAT-008 (Invoicing) — Core invoice lifecycle, line items, numbering, PDF generation.
- FEAT-015 (Advances, Ledger Transactions & General Invoices) — General invoices concept (nullable `project_id`).
