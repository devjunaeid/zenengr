---
id: TODO-120
title: Activity history UI component
feature: FEAT-011
story: US-045
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-119]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-120 — Activity history UI component

## Description

Build activity history component on profile/settings page. Shows email changes and password changes with timestamps. User sees only own history.

## Acceptance criteria

- [x] GET /api/auth/activity returns user's activity history.
- [x] UI list: event type icon, timestamp, description.
- [x] Email change entry shows old and new email (FR-11.5).
- [x] Password change entry shows timestamp only.
- [x] Read-only log — no delete.

## Notes

Activity history tables on both profile pages (read-only, event + old/new values).

