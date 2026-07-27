---
id: TODO-117
title: Notification preference UI
feature: FEAT-011
story: US-044
status: proposed
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

- [ ] Preferences page: toggle per event type with label (FR-11.3).
- [ ] All toggles default ON.
- [ ] Toggle change calls PATCH /api/auth/notification-preferences/{event_type}.
- [ ] Preferences page accessible from profile settings.
- [ ] System notifications (password changes, etc.) not toggleable (US-044 Notes).

## Notes

