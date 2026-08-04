---
id: TODO-118
title: Preference-aware notification dispatch
feature: FEAT-011
story: US-044
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-107, TODO-116]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-118 — Preference-aware notification dispatch

## Description

Ensure notification dispatch service (TODO-107) checks user's NotificationPreference before sending. Users with event disabled do not receive notifications.

## Acceptance criteria

- [x] Before sending notification: query NotificationPreference for user + event_type.
- [x] If enabled=false: skip email for that user.
- [x] Checked per-user, per-event.
- [x] Integrates with TODO-107 dispatch service.

## Notes

Prefs-aware dispatch active via dispatch_new_comment (TODO-108 wiring); other event types dispatch when their producers land.

