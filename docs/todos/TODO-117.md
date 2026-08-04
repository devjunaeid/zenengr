---
id: TODO-117
title: Notification preference UI
feature: FEAT-011
story: US-044
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-116]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-117 — Notification preference UI

## Description

Build notification preferences page with toggle switches for each event type. Accessible from both Admin Portal and Client Portal profile.

## Acceptance criteria

- [x] Preferences page: toggle per event type with label (FR-11.3).
- [x] All toggles default ON.
- [x] Toggle change calls PATCH /api/auth/notification-preferences/{event_type}.
- [x] Preferences page accessible from profile settings.
- [x] System notifications (password changes, etc.) not toggleable (US-044 Notes).

## Notes

Prefs toggle UI on both profile pages (immediate PATCH, per-event saved flash).

