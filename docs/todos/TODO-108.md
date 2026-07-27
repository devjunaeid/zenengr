---
id: TODO-108
title: Preference-aware notification filtering
feature: FEAT-010
story: US-041
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-107, TODO-116]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-108 — Preference-aware notification filtering

## Description

Ensure notification dispatch respects per-user notification preferences (TODO-116). Users who disabled "new comment" notifications do not receive emails.

## Acceptance criteria

- [ ] Before dispatching: check user's notification_preferences for the event type.
- [ ] If disabled: skip email for that user.
- [ ] Preferences checked per user (not per-tenant).
- [ ] Default: all notifications enabled (TODO-116).

## Notes

