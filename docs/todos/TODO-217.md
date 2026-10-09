---
id: TODO-217
title: Search and Filter Debouncing Across All Listing Views
story: US-074
feature: FEAT-026
status: proposed
priority: P1
dependencies: []
blocks: []
---

# TODO-217 - Search and Filter Debouncing Across All Listing Views

## Context

On Slow 3G networks (high round-trip latency ~400ms), user typing in list filters and comboboxes triggers rapid back-to-back API calls, causing request queues, stale response race conditions, and sluggish UI response.

## Scope

- Implement or update a reusable search debouncer utility (`debounce` helper or reactive timer in Svelte 5).
- Integrate 250-300ms debounce on search inputs across `/app/clients`, `/app/projects`, `/app/invoices`, `/app/reports`, `/app/team`, and `/app/settings/services`.
- Ensure cancellation/ignoring of stale query requests when newer terms are entered.

## Acceptance check

Typing rapidly in search fields does not fire network requests on every keypress; only a single request fires 250-300ms after typing halts.
