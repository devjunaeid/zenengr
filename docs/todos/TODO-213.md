---
id: TODO-213
story: US-072
feature: FEAT-025
title: Backend SQL aggregation service & API endpoint (GET /tenant/reports/company-ledger)
status: done
priority: P1
dependencies: []
blocks: [TODO-214, TODO-215, TODO-216]
---

# TODO-213 - Backend SQL aggregation service & API endpoint (GET /tenant/reports/company-ledger)

## What to do

1. Create schema models in `backend/app/schemas/reports.py`:
   - `CompanyLedgerSummary`: new projects, new clients, new services count and value, total invoiced, total collected, total due, total advance balance.
   - `CompanyLedgerTimelineItem`: period label, new projects, new clients, new services, invoiced, collected, due change.
   - `CompanyLedgerProjectItem`: project_id, short_id, name, client_id, client_name, status, services_count, total_value, total_invoiced, total_paid, balance_due.
   - `CompanyLedgerClientItem`: client_id, name, client_type, active_projects, services_count, total_invoiced, total_paid, total_due, advance_balance.
   - `CompanyLedgerResponse`: summary, timeline, projects, clients, filters applied.
2. Implement aggregation service `backend/app/services/reports.py`:
   - Efficient tenant-scoped queries aggregating metrics by date range (`date_from`, `date_to`), optional `client_id`, optional `project_id`.
   - Calculate summary KPIs in a single or small batch of indexed aggregate queries.
   - Generate timeline series using `date_trunc('month', ...)` or day-based truncation.
   - Compute project-wise and client-wise rollup lists.
3. Add router endpoint in `backend/app/api/v1/reports.py`:
   - Mount at `/tenant/reports/company-ledger`.
   - Require `view/financial_reports` permission.
   - Include router in `backend/app/main.py`.
4. Add unit / integration tests in `backend/tests/test_reports_api.py`.

## Acceptance Check

- Endpoint returns 200 with complete summary, timeline, projects, and clients data.
- Enforces tenant isolation and permission check (`view/financial_reports`).
- Date filtering correctly limits new projects, clients, invoices, and payments to the specified interval.
- Targeted pytest tests pass 100%.
