---
id: TODO-194
title: Copy icon assets, create manifest.webmanifest, and configure HTML PWA headers
feature: FEAT-020
story: US-065
status: done
priority: P1
owner: ""
estimate: "1h"
dependencies: []
blocks: [TODO-195, TODO-196]
created: "2026-09-08"
updated: "2026-09-08"
---

# TODO-194 — Copy icon assets, create manifest.webmanifest, and configure HTML PWA headers

## Description

- Copy icons from `docs/dev/icons/` to `frontend/static/icons/` (or `frontend/static/`):
  - `zenengr-icon-512x512.png` -> `icon-512.png`
  - `zenengr-icon-192x192.png` -> `icon-192.png`
  - `zenengr-icon-32x32.png` -> `favicon.png`
  - `zenengr-balanced-monolith-indigo-violet.svg` -> `icon.svg`
  - Create standard Apple touch icon copy (`apple-touch-icon.png`).
- Create `frontend/static/manifest.webmanifest` defining:
  - `name`: "ZenEngr — Engineering & Service Ops Platform"
  - `short_name`: "ZenEngr"
  - `start_url`: "/"
  - `display`: "standalone"
  - `background_color`: "#f8fafc"
  - `theme_color`: "#4f46e5"
  - `icons`: standard list of 192x192, 512x512 (both `any` and `maskable`), and SVG.
- Update `frontend/src/app.html` to link the manifest, favicon, apple-touch-icon, and set `theme-color` & `apple-mobile-web-app-*` meta tags.

## Acceptance criteria

- [x] `manifest.webmanifest` is valid JSON and served at `/manifest.webmanifest`.
- [x] Browser DevTools -> Application -> Manifest shows valid icons and metadata without warnings.
- [x] iOS Safari and desktop browsers recognize the favicon and touch icon.
