---
id: TODO-107
title: Notification dispatch service
feature: FEAT-010
story: US-041
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-106]
blocks: [TODO-108]
created: "2026-07-26"
updated: "2026-08-03"
---

# TODO-107 — Notification dispatch service

## Description

Build notification dispatch service that sends emails for relevant events. Triggered on new shared comment. Checks notification preferences before sending.

## Acceptance criteria

- [x] Service method: dispatch_notification(event_type, entity_id, excludes_user_id).
- [x] On new shared comment: dispatches to project participants (staff + client user).
- [x] Checks user's notification preferences (TODO-116) before sending.
- [x] Client users only notified for shared comments on their own projects (FR-10.5).

## Notes

dispatch_new_comment in app/services/notifications.py: recipients = active tenant staff + active client users of project's client, excludes author; admin vs client portal base URLs; email failures swallowed (never break comment post). TODO-108 still needs TODO-116 prefs model.

