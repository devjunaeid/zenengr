---
id: TODO-116
title: Notification preference model
feature: FEAT-011
story: US-044
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-108, TODO-117, TODO-118]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-116 — Notification preference model

## Description

Create NotificationPreference model per user: event_type (new_comment, invoice_issued, payment_received, milestone_completed) + enabled bool. Defaults all enabled.

## Acceptance criteria

- [ ] NotificationPreference model: id, user_id FK, event_type enum, enabled bool (default true), timestamps.
- [ ] Alembic migration creates table.
- [ ] On user creation: seed defaults for all event types (all enabled) (FR-11.3).
- [ ] Event types: new_comment, invoice_issued, payment_received, milestone_completed.

## Notes

