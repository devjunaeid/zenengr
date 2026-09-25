---
id: TODO-211
story: US-070
feature: FEAT-024
title: Refactor Client Portal Project View (/client/projects/[id]) for lazy tab loading
status: done
priority: P1
dependencies: []
blocks: []
---

# TODO-211 - Refactor Client Portal Project View (/client/projects/[id]) for lazy tab loading

## What to do

1. Update `frontend/src/routes/client/projects/[id]/+page.js`:
   - Load only `project` data upfront. Remove upfront loading of `files` and `ledger`.
2. Update `frontend/src/routes/client/projects/[id]/+page.svelte`:
   - Add on-demand loaders for `ledger` and `files` on tab click.
   - Cache results in component state.
3. Validate client portal project view renders quickly and tabs work smoothly.

## Acceptance Check

- Navigating to `/client/projects/[id]` renders the project overview and milestones instantly.
- Financials tab loads ledger on demand.
- Files tab loads files on demand.
