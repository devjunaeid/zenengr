---
id: TODO-209
story: US-070
feature: FEAT-024
title: Refactor Staff Project Details (/app/projects/[id]) for lazy tab loading and client caching
status: done
priority: P1
dependencies: []
blocks: []
---

# TODO-209 - Refactor Staff Project Details (/app/projects/[id]) for lazy tab loading and client caching

## What to do

1. Update `frontend/src/routes/app/projects/[id]/+page.js`:
   - Strip out initial loading of `users`, `ledger`, `invoices`, `projectFiles`, `folderTree`, and `projectRoles`.
   - Only fetch `project`, `client`, and `overview` initially.
   - Return clean default placeholders for tab datasets.
2. Update `frontend/src/routes/app/projects/[id]/+page.svelte`:
   - Add state management and loaders for individual tabs (`loadLedgerTab`, `loadInvoicesTab`, `loadFilesTab`, `loadTeamTab`).
   - Check if tab data is already cached before fetching; show inline Spinner/skeleton if fetching for the first time.
   - If initial URL contains a query param like `?tab=ledger`, trigger the respective tab fetch immediately.
   - Update `refreshFinancials` to update data cleanly without breaking lazy cache.
3. Validate tab switching, data integrity, and fast page loads.

## Acceptance Check

- Navigating to `/app/projects/[id]` completes quickly without waiting for files, invoices, ledger, or users.
- Clicking Ledger tab loads ledger on demand and caches it.
- Clicking Invoices tab loads invoices on demand and caches it.
- Clicking Files tab loads files and folders on demand and caches them.
- Clicking Team tab loads users and roles on demand and caches them.
- Switching between loaded tabs has zero delay and makes zero duplicate requests.
