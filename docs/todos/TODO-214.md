---
id: TODO-214
story: US-073
feature: FEAT-025
title: Frontend /app/reports page layout, KPI cards, date range & filter toolbar
status: done
priority: P1
dependencies: [TODO-213]
blocks: [TODO-215, TODO-216]
---

# TODO-214 - Frontend /app/reports page layout, KPI cards, date range & filter toolbar

## What to do

1. Add "Reports" item to sidebar navigation in `frontend/src/routes/app/+layout.svelte` with `poll` / `chartBoxOutline` icon and permission gate `['view', 'financial_reports']`.
2. Add API client method in `frontend/src/lib/api/reports.js`:
   - `getCompanyLedger(fetchFn, token, params)`
3. Create route files `frontend/src/routes/app/reports/+page.js` and `+page.svelte`:
   - `+page.js`: Read query params (`date_from`, `date_to`, `preset`, `client_id`, `project_id`), default to *This Month*, fetch company ledger data.
   - `+page.svelte`: Header with title, subtitle, date presets pill selector (*This Month*, *Last Month*, *This Quarter*, *YTD*, *All Time*, *Custom*), and custom date pickers.
   - Client and Project picker combobox filters.
   - Executive KPI cards grid displaying:
     1. New Projects
     2. New Services
     3. New Clients
     4. Total Invoiced
     5. Payments Collected
     6. Net Outstanding Due
     7. Advance Credit Held
   - Tab switcher for: **Timeline (Month-wise)**, **Projects Breakdown**, **Clients Breakdown**.

## Acceptance Check

- Navigation item displays for admin and manager roles.
- Changing date presets updates query parameters and refreshes KPI numbers reactively.
- Reset filters button clears all filters back to current month defaults.
- Clean responsive layout on mobile, tablet, and desktop.
