---
id: TODO-200
story: US-066
feature: FEAT-021
status: done
priority: P1
assignee: ""
created: "2026-09-09"
updated: "2026-09-09"
---

# TODO-200 — Frontend invoices list filtering: Type selector, optional date range filter, and Billed-To display in detail/list views

## Context

On the Invoices directory page (`/app/invoices`), users need to filter invoices by type (All, Project, General) and by date range (From Date, To Date), alongside existing status and project filters. Users also need to see the recipient name on General Invoices in listings, detail views, and edit views.

## Acceptance criteria

- [x] Invoice list filter bar includes Type selector (All, Project, General) and optional Date Range inputs (`date_from`, `date_to`).
- [x] Active filters trigger filtered data fetch with clean URL synchronization and quick Reset action.
- [x] Table and responsive mobile cards display Billed-To recipient name for General Invoices.
- [x] Invoice detail view (`/app/invoices/[id]`) and edit view (`/app/invoices/[id]/edit`) display and allow editing `billed_to` information for General Invoices.
