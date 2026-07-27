---
id: TODO-107
title: Notification dispatch service
feature: FEAT-010
story: US-041
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-106]
blocks: [TODO-108]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-107 — Notification dispatch service

## Description

Build notification dispatch service that sends emails for relevant events. Triggered on new shared comment. Checks notification preferences before sending.

## Acceptance criteria

- [ ] Service method: dispatch_notification(event_type, entity_id, excludes_user_id).
- [ ] On new shared comment: dispatches to project participants (staff + client user).
- [ ] Checks user's notification preferences (TODO-116) before sending.
- [ ] Client users only notified for shared comments on their own projects (FR-10.5).

## Notes

