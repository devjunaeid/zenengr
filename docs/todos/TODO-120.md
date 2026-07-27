---
id: TODO-120
title: Activity history UI component
feature: FEAT-011
story: US-045
status: proposed
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

- [ ] GET /api/auth/activity returns user's activity history.
- [ ] UI list: event type icon, timestamp, description.
- [ ] Email change entry shows old and new email (FR-11.5).
- [ ] Password change entry shows timestamp only.
- [ ] Read-only log — no delete.

## Notes

