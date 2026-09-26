---
id: TODO-215
story: US-073
feature: FEAT-025
title: Date/Month-wise timeline view & operational trend breakdown
status: done
priority: P1
dependencies: [TODO-214]
blocks: []
---

# TODO-215 - Date/Month-wise timeline view & operational trend breakdown

## What to do

1. Build timeline table and trend visualizer component in `frontend/src/routes/app/reports/+page.svelte`:
   - Lists periods chronologically (e.g. Sep 2026, Aug 2026, or individual dates if scoped to a short window).
   - Columns: Period, New Projects, New Clients, New Services, Invoiced Amount, Collected Amount, Net Due Generated.
   - Inline relative visual bars comparing Invoiced vs Collected volume for each period.
   - Highlights net positive collections in emerald and net pending dues in amber.
2. Provide period summary row with column totals at bottom of table.
3. Ensure zero-data state displays an informative empty state card.

## Acceptance Check

- Timeline rows accurately reflect the monthly/daily metrics from the backend.
- Comparison bars render cleanly and adapt responsively across viewport widths.
- Column totals match executive KPI card totals.
