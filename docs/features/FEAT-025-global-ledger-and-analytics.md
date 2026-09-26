---
id: FEAT-025
title: Company Global Ledger & Operational Analytics Dashboard
status: completed
priority: P1
source: User requirement 2026-09-26
---

# FEAT-025 - Company Global Ledger & Operational Analytics Dashboard

## Goal

Provide company administrators and managers with a centralized, read-only reporting and analysis dashboard ("Global Ledger & Analytics") to inspect organization-wide performance from a single place. The dashboard delivers:
1. Executive KPI metrics across any selected date range: new projects created, new services initiated, new clients onboarded, total invoiced, payments collected, and net outstanding dues.
2. Multi-dimensional breakdowns:
   - **Month / Date-wise:** Chronological trend of operational growth, invoicing, and collections.
   - **Project-wise:** Financial performance and receivables per project.
   - **Client-wise:** Cumulative billing, payments, dues, and advance balances per client.
3. Flexible filtering (date range presets, custom dates, client, project) and CSV export for external bookkeeping and analysis.
4. Strictly read-only: no creation or modification operations are conducted on this reporting page.

## Scope

### In Scope

- **Backend Aggregation Service & API (`/api/v1/tenant/reports/company-ledger`):**
  - High-performance, tenant-scoped SQL aggregation queries computing summary KPIs, chronological time-series (by month or day), project-level summaries, and client-level summaries.
  - Query parameters: `date_from`, `date_to`, `client_id`, `project_id`, `granularity` (`month` or `day`).
  - Strict RBAC: Protected by `view/financial_reports` (Admin and Manager access).
- **Frontend Dedicated View (`/app/reports`):**
  - New sidebar navigation item under `/app` labeled **Reports** guarded by `perm: ['view', 'financial_reports']`.
  - Date range selector with presets: *This Month*, *Last Month*, *This Quarter*, *This Year (YTD)*, *Last 30 Days*, *Last 90 Days*, *All Time*, and *Custom Date Range*.
  - Entity filters: Client filter and Project filter.
  - Executive KPI Cards: Total New Projects, Total New Services, Total New Clients, Total Invoiced, Total Payments Collected, Net Outstanding Dues, and Total Advance Credits.
  - Three tabbed perspectives:
    1. **Timeline (Month / Date-wise):** Visual bar/metric trend comparing billing vs collections and new entities over time.
    2. **Project Breakdown:** Tabular ledger of projects with total value, invoiced, paid, balance due, and client link.
    3. **Client Breakdown:** Tabular ledger of clients with project count, invoiced, paid, balance due, and advance credit.
  - CSV Export: Client-side download of the active report dataset for accounting.

### Out of Scope

- Transaction creation, invoice generation, or manual ledger adjustments from this view (strictly read-only reporting).
- Complex external BI integrations or third-party charting libraries (uses sleek modern Tailwind/HTML native visualizations to keep bundle size minimal).

## Functional Requirements

- **FR-25.1:** Accessible only to users with `view` permission on `financial_reports` (Tenant Admin and Manager roles).
- **FR-25.2:** Supports flexible date range filtering defaulting to *This Month*, while allowing quick toggles for *Last Month*, *This Quarter*, *YTD*, *All Time*, and custom start/end dates.
- **FR-25.3:** Summary KPIs must compute accurately within the selected date window:
  - Count of projects created with `created_at` in range.
  - Count and total value of project services attached with `created_at` in range.
  - Count of clients created with `created_at` in range.
  - Sum of issued invoice amounts issued in range.
  - Sum of debit transactions minus refund credit transactions recorded in range.
  - Net outstanding receivables as of the period end.
- **FR-25.4:** Timeline breakdown groups data chronologically (`date_trunc('month', ...)` or by day for ranges <= 31 days).
- **FR-25.5:** Project and Client tables support real-time text search and sorting by highest due, highest paid, highest invoiced, or name.
- **FR-25.6:** One-click CSV export generates formatted tabular files for the current view and filter selection.

## Acceptance Criteria

1. Navigating to `/app/reports` displays the executive KPI cards and default current month analytics in < 500ms.
2. Toggling date presets or picking a custom date range updates all cards, timeline metrics, and tables consistently.
3. Filtering by a specific client or project recalculates the metrics and tables to reflect only that entity's scope.
4. Month/Date-wise breakdown accurately reflects monthly new projects, new clients, services, billing, collections, and dues.
5. Project-wise and Client-wise tables accurately display individual and aggregate numbers matching the individual entity ledgers.
6. Non-admin/non-manager roles (e.g. employee) without `financial_reports` permission cannot access the route or API endpoint.
7. CSV export downloads clean, well-formatted CSV reports.
