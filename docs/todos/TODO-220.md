---
id: TODO-220
title: Service Worker Cache & Image/Icon Performance Optimization
story: US-074
feature: FEAT-026
status: proposed
priority: P1
dependencies: []
blocks: []
---

# TODO-220 - Service Worker Cache & Image/Icon Performance Optimization

## Context

Static assets, SVG icons, and user avatars should load with minimal latency on Slow 3G and offline modes.

## Scope

- Enhance `service-worker.js` to ensure versioned cache warming for critical UI shell assets and fonts.
- Add `loading="lazy"` and `decoding="async"` across avatar images and logos.
- Verify SvelteKit link preload strategies across main layout navigation items.

## Acceptance check

App shell assets load from cache with sub-50ms latency on repeated visits; images and icons do not block initial text rendering on Slow 3G.
