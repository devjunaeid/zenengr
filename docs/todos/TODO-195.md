---
id: TODO-195
title: Implement SvelteKit service worker with app shell pre-caching and asset versioning
feature: FEAT-020
story: US-065
status: done
priority: P1
owner: ""
estimate: "2h"
dependencies: [TODO-194]
blocks: [TODO-196]
created: "2026-09-08"
updated: "2026-09-08"
---

# TODO-195 — Implement SvelteKit service worker with app shell pre-caching and asset versioning

## Description

- Implement `frontend/src/service-worker.js` using SvelteKit's `$service-worker` primitives:
  - Import `build`, `files`, and `version`.
  - Cache name keyed by version: `cache-zenengr-${version}`.
  - Install event: pre-cache static files and build output (`build`, `files`).
  - Activate event: clean up stale caches from older versions; call `clients.claim()`.
  - Fetch event:
    - Exclude `/api/` and WebSocket `/ws/` requests (always bypass to network).
    - Cache-first or Stale-While-Revalidate for immutable assets (`/_app/*`, static images/icons).
    - Network-first with cached app shell fallback for navigation requests (`mode === 'navigate'`).

## Acceptance criteria

- [x] Service worker successfully registers in the browser and activates.
- [x] Static assets and app shell load instantly from cache on repeated loads.
- [x] API calls (`/api/v1/*`) and WebSocket traffic pass through unaltered to the backend.
- [x] Deploying an asset version update flushes obsolete cached versions.
