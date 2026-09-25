---
id: TODO-210
story: US-070
feature: FEAT-024
title: Refactor Staff Client Details (/app/clients/[id]) for lazy tab loading
status: done
priority: P1
dependencies: []
blocks: []
---

# TODO-210 - Refactor Staff Client Details (/app/clients/[id]) for lazy tab loading

## What to do

1. Update `frontend/src/routes/app/clients/[id]/+page.js`:
   - Do not load `notes`, `activity`, and `ledger` during the initial load if the active tab is overview.
   - Or make them load on demand from `+page.svelte` when those tabs are clicked.
2. Update `frontend/src/routes/app/clients/[id]/+page.svelte`:
   - Add on-demand loaders for `ledger`, `notes`, and `activity` with local caching.
   - Show inline spinner during initial tab data fetch.
3. Validate client overview renders instantly and secondary tabs load smoothly on demand.

## Acceptance Check

- Navigating to `/app/clients/[id]` only loads client info upfront.
- Financials tab loads ledger on first click.
- Notes and Activity tabs load on first click and cache pagination state.
