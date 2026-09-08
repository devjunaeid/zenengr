---
id: TODO-196
title: Add in-app install trigger helper and offline connectivity banner
feature: FEAT-020
story: US-065
status: done
priority: P1
owner: ""
estimate: "1.5h"
dependencies: [TODO-195]
blocks: []
created: "2026-09-08"
updated: "2026-09-08"
---

# TODO-196 — Add in-app install trigger helper and offline connectivity banner

## Description

- Create a reactive PWA store (`$lib/stores/pwa.svelte.js`) capturing:
  - `beforeinstallprompt` event (storing the prompt event to enable custom "Install App" triggers).
  - Online/offline status using `navigator.onLine` and `window.addEventListener('online'/'offline')`.
  - Install state (whether already running in `window.matchMedia('(display-mode: standalone)').matches` or standalone mode).
- Add an `OfflineBanner.svelte` or global toast component in `+layout.svelte` showing a subtle, non-blocking warning when the internet connection drops, and auto-dismissing when back online.
- Add an optional "Install App" action or banner when available (dismissible).

## Acceptance criteria

- [x] Disconnecting internet displays a clean "You're offline" indicator; reconnecting hides it.
- [x] In browsers supporting `beforeinstallprompt`, the install event is captured and can be triggered via user action.
- [x] If already running in standalone mode (installed PWA), install prompts are suppressed.
