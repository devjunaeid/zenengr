---
id: TODO-216
story: US-073
feature: FEAT-025
title: Project-wise & Client-wise breakdown tables with search, sorting, and CSV export
status: done
priority: P1
dependencies: [TODO-214]
blocks: []
---

# TODO-216 - Project-wise & Client-wise breakdown tables with search, sorting, and CSV export

## What to do

1. Build Project Breakdown Tab in `frontend/src/routes/app/reports/+page.svelte`:
   - Search input filtering projects by name or client.
   - Sort dropdown/controls: Highest Due, Highest Paid, Highest Invoiced, Name.
   - Table columns: Project Name & Short ID, Client Name, Status Badge, Attached Services Count, Total Project Value, Invoiced, Paid, Balance Due.
   - Clickable links directing directly to `/app/projects/[id]`.
2. Build Client Breakdown Tab in `frontend/src/routes/app/reports/+page.svelte`:
   - Search input filtering clients by name.
   - Sort dropdown/controls: Highest Due, Highest Invoiced, Most Projects, Name.
   - Table columns: Client Name, Client Type, Active Projects Count, Services Count, Total Invoiced, Total Paid, Balance Due, Advance Credit.
   - Clickable links directing directly to `/app/clients/[id]`.
3. Add CSV Export button:
   - Exports the active tab's data (Timeline, Projects, or Clients) as a downloaded `.csv` file with current date timestamp.

## Acceptance Check

- Project and Client tables allow quick searching and sorting without re-fetching from server.
- Clicking any row navigates directly to that project or client detail view.
- CSV export downloads a valid, cleanly formatted CSV file matching the currently active table.
