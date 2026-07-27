---
id: TODO-118
title: Preference-aware notification dispatch
feature: FEAT-011
story: US-044
status: proposed
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

- [ ] Before sending notification: query NotificationPreference for user + event_type.
- [ ] If enabled=false: skip email for that user.
- [ ] Checked per-user, per-event.
- [ ] Integrates with TODO-107 dispatch service.

## Notes

