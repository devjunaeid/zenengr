---
id: FEAT-026
title: Mobile Performance, Slow 3G Network Efficiency & Touch UX Optimization
status: proposed
priority: P1
source: User requirement 2026-10-09
---

# FEAT-026 - Mobile Performance, Slow 3G Network Efficiency & Touch UX Optimization

## Goal

Optimize the entire platform across all modules (Clients, Projects, Invoices, Reports, Team, Settings, and Client Portal) to deliver exceptional responsiveness, low-latency performance on constrained mobile/Slow-3G network connections, and top-notch mobile touch user experiences.

Key objectives:
1. **Slow-3G Network Efficiency & Resilience:**
   - Eliminate redundant network roundtrips, heavy eager fetches, and waterfall loading.
   - Introduce request debouncing and deduplication on search bars, filters, and comboboxes.
   - Implement graceful loading states, progressive rendering, and skeleton screens to eliminate jarring Cumulative Layout Shift (CLS).
   - Leverage Service Worker caching and SvelteKit route prefetching for near-instant navigation.
2. **Top-Notch Mobile Flow & Touch UX:**
   - Mobile-first ergonomic touch flows: Ensure all interactive buttons, links, and form controls satisfy the minimum 44×44px touch target area.
   - Sticky mobile action bars on long forms (e.g. client creation, invoice generator, project edit) so users can submit or cancel without extensive scrolling.
   - Sleek responsive mobile card views and off-canvas drawers across all modules.
   - Virtual keyboard optimizations (`inputmode`, `enterkeyhint`, `autocomplete`) across all form inputs.

## Scope

### In Scope

- **Frontend Network & Caching Optimization (`frontend/src/`):**
  - Search & filter debouncing: Unified 250-300ms debounce across all search inputs (Clients, Invoices, Projects, Reports, Services, Team).
  - Skeleton loading components: Replace blank flashes or blocking spinners with progressive skeleton placeholders for tables and cards.
  - SvelteKit navigation preload optimization (`data-sveltekit-preload-data="hover"` and prefetch on touchstart/tap).
  - Service worker asset caching enhancement for offline/flaky 3G network shell delivery.
  - Image and avatar loading optimization (`loading="lazy"`, `decoding="async"`, fallback dimensions).
- **Mobile Touch UX & Flow Overhaul:**
  - Sticky mobile action bar on key forms (`/app/clients/new`, `/app/clients/[id]/edit`, `/app/invoices/new`, `/app/projects/new`) with safe-area bottom padding.
  - Viewport-aware off-canvas drawer navigation and mobile notification popover bounds.
  - Minimum 44×44px tap targets for pagination controls, action buttons, table menus, and tab bars.
  - Mobile card views: Ensure financial figures, statuses, and key metadata are scan-friendly and thumb-navigable.
- **Backend Response Efficiency (`backend/app/`):**
  - Lean responses: Verify list endpoints only query and project necessary columns, leveraging existing index scans.
  - Compression & cache headers verification for static and immutable assets.

### Out of Scope

- Offline-first data mutation syncing with local IndexedDB queue (mutations still require live API connection; read-only shell is cached).
- Native iOS/Android app wrappers (PWA remains the primary mobile install channel).

## Functional Requirements

- **FR-26.1:** All text search and filter inputs across list views must debounce requests by 250-300ms to eliminate redundant API spamming over high-latency 3G networks.
- **FR-26.2:** All major listing views (Clients, Projects, Invoices, Reports) must present progressive skeleton loaders while fetching on slow connections.
- **FR-26.3:** Long creation and editing forms on mobile must provide a sticky bottom action bar (with Cancel and Primary Action) respecting `env(safe-area-inset-bottom)` so mobile users have instant access to actions.
- **FR-26.4:** All mobile buttons, tab items, dropdown triggers, and pagination buttons must satisfy the 44×44px minimum touch target size.
- **FR-26.5:** Table views must gracefully adapt to responsive card grids on screens `< lg` (or `< md` where appropriate) without horizontal scrolling traps.
- **FR-26.6:** Service worker shell caching must serve app assets with low latency, falling back to network gracefully.

## Acceptance Criteria

1. On simulated Slow 3G (Chrome DevTools Throttling: 400ms RTT, 400kbps down), initial page load renders the interactive shell with zero layout shift, displaying skeleton loaders before data renders.
2. Search and filter inputs do not trigger an API request on every character keystroke; network queries fire only after typing pauses.
3. On mobile viewport (390×844px), all forms can be submitted via accessible sticky or clearly visible buttons without layout overlap.
4. Form inputs on iOS Safari and mobile Chrome do not cause unwanted zoom, text clipping, or keyboard occlusion.
5. All targeted lints, type checks, and tests pass with 0 errors.
