---
id: FEAT-024
title: Lazy Loading Tabbed Views & Lean On-Demand API Architecture
status: completed
priority: P1
source: User requirement 2026-09-26
---

# FEAT-024 - Lazy Loading Tabbed Views & Lean On-Demand API Architecture

## Goal

1. Eliminate long initial page load times across multi-tab views (Project Details, Client Details, Client Portal Project View) by lazy-loading secondary tab data on-demand upon first click, rather than blocking the initial render with a monolithic `Promise.all` containing up to 9 parallel API calls.
2. Implement local in-memory caching for lazy-loaded tabs so switching back to an already-visited tab is instant (0ms delay) without redundant network requests.
3. Streamline backend endpoints to return lean, bare-minimum payloads by default, reducing unnecessary database queries, joins, and payload size.

## Scope

### In Scope

- **Project Details View (`/app/projects/[id]`):**
  - Streamline initial route loader (`+page.js`): Load only essential project information (`project`, `client`, and initial tab data).
  - Remove upfront fetching of `users` (100 rows), `ledger` (full project transaction stream), `invoices` (100 rows), `projectFiles` (100 files), `folderTree`, and `projectRoles`.
  - Lazy-load each tab's data dynamically on first tab click (with clean skeleton/spinner states), caching resolved data in local component state.
  - Wire fast financial refresh (`refreshFinancials`) to only re-query the currently active tab or affected datasets.
- **Client Details View (`/app/clients/[id]`):**
  - Streamline initial route loader (`+page.js`): Load only core client details and overview data.
  - Lazy-load `notes`, `activity`, and `client ledger` when the user clicks the Financials, Notes, or Activity tab, rather than loading all three upfront in `Promise.all`.
- **Client Portal Project View (`/client/projects/[id]`):**
  - Streamline initial route loader (`+page.js`): Load only project info upfront.
  - Lazy-load `ledger` and `files` on-demand upon tab activation.
- **Lean API Queries & Payloads:**
  - Audit high-frequency endpoints (`/projects/{id}`, `/clients/{id}`, `/invoices`, `/files`) to ensure queries only select required columns and relationships.

### Out of Scope

- Removing tabs or altering the visual design of existing tab bars.
- Replacing REST with GraphQL.

## Functional Requirements

- **FR-24.1:** Navigating to `/app/projects/[id]` must only wait for core project entity data before rendering the page shell and initial tab.
- **FR-24.2:** Clicking secondary tabs on Project Details (Ledger, Invoices, Files, Team) fetches that tab's data on-demand on first activation, displaying a subtle inline loader while fetching.
- **FR-24.3:** Once a tab's data has loaded, subsequent switches back and forth between tabs must be instant (no re-fetching or flickering).
- **FR-24.4:** Client Details (`/app/clients/[id]`) must only fetch Financials (ledger), Notes, or Activity when their respective tab is selected.
- **FR-24.5:** Client Portal Project Details (`/client/projects/[id]`) must lazy-load Files and Financials on tab click.

## Acceptance Criteria

1. Navigating to `/app/projects/[id]` loads in < 300ms without firing all 9 API calls simultaneously.
2. Clicking the Invoices, Ledger, Files, or Team tab loads the corresponding data smoothly on first click and caches it.
3. Switching between previously loaded tabs is instantaneous without duplicate API requests.
4. Client details and client portal project views exhibit the same on-demand loading and caching behavior.
5. All backend and frontend tests and linters pass cleanly.
