---
id: FEAT-020
title: Progressive Web App (PWA) & Web App Install Support
status: approved
priority: P1
source: User requirement 2026-09-08
---

# FEAT-020 — Progressive Web App (PWA) & Web App Install Support

## Goal

Provide a seamless, installable desktop and mobile Progressive Web App (PWA) experience for ZenEngr. Allow staff and client portal users to install ZenEngr directly to their desktop dock/taskbar or mobile home screen, running in a standalone, borderless window with zero-latency app-shell startup, integrated ZenEngr brand icons, offline connectivity detection, and background cache management.

## Functional Requirements

- **FR-20.1: Web App Manifest.** Provide a standard `manifest.webmanifest` defining `name: "ZenEngr"`, `short_name: "ZenEngr"`, `start_url: "/"`, `display: "standalone"`, `background_color: "#f8fafc"`, and `theme_color: "#4f46e5"`.
- **FR-20.2: Brand Icon Integration.** Deploy the balanced-monolith SVG and PNG icons from `docs/dev/icons/` to `frontend/static/` for high-resolution 512x512, 192x192, 32x32 favicon, and iOS Apple Touch Icon.
- **FR-20.3: SvelteKit Service Worker & App Shell Caching.** Implement `src/service-worker.js` leveraging SvelteKit's `$service-worker` (`build`, `files`, `version`) to pre-cache the static app shell bundle (HTML, JS, CSS, icons) while routing API requests (`/api/v1/*`) and WebSocket connections (`/ws/*`) directly to the network.
- **FR-20.4: Native PWA Meta & Splash Screen Integration.** Update `frontend/src/app.html` with mobile browser meta tags (`apple-mobile-web-app-capable`, `apple-mobile-web-app-status-bar-style`, `theme-color`, favicon, and manifest link) harmonized with the existing `#app-boot-loader` splash screen.
- **FR-20.5: In-App Install Prompt.** Listen for the browser `beforeinstallprompt` event and provide a lightweight, dismissible prompt or settings button allowing users to trigger native installation on Chrome, Edge, and Android.
- **FR-20.6: Online/Offline Status Indicator.** Provide clean in-app awareness when network connectivity is lost, displaying a subtle offline warning without corrupting financial forms or failing silently.

## Acceptance Criteria

1. Navigating to the app in supported browsers (Chrome, Edge) presents the native install button in the address bar ("Install ZenEngr"). (FR-20.1)
2. Installing launches ZenEngr in a dedicated standalone window with the official ZenEngr monolith icon and no browser URL bar. (FR-20.1, FR-20.2)
3. The service worker installs and pre-caches the static app shell, updating automatically when new frontend versions deploy. (FR-20.3)
4. API calls and WebSocket connections bypass service worker caching and hit the backend directly. (FR-20.3)
5. Apple devices (Safari iOS/macOS) recognize the app for "Add to Home Screen" with the custom icon and standalone display mode. (FR-20.4)
6. If the device goes offline, the UI remains responsive and displays an offline status notification. (FR-20.6)

## Dependencies

- FEAT-000 (Local Development Environment & Frontend Skeleton)
- Existing SPA architecture (`@sveltejs/adapter-static`, `ssr = false`)
