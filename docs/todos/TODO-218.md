---
id: TODO-218
title: Progressive Skeleton Placeholders for Slow 3G Connections
story: US-074
feature: FEAT-026
status: proposed
priority: P1
dependencies: []
blocks: []
---

# TODO-218 - Progressive Skeleton Placeholders for Slow 3G Connections

## Context

When navigating between modules on slow connections, pages can flash blank or cause severe Cumulative Layout Shift (CLS) when data arrives. Providing polished skeleton placeholders keeps perceived performance instant.

## Scope

- Create a shared `TableSkeleton.svelte` and `CardListSkeleton.svelte` component supporting configurable columns and card shapes.
- Integrate skeletons into `/app/clients`, `/app/projects`, `/app/invoices`, `/app/reports`, and detail view tab panels (`/app/projects/[id]`, `/app/clients/[id]`).
- Ensure skeleton transitions smoothly into real data without jarring layout jumps.

## Acceptance check

Simulating Slow 3G shows elegant animated skeleton bars occupying the exact dimensions of data tables and cards during loading states.
