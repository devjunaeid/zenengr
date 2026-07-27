---
id: TODO-119
title: User activity history model + logging
feature: FEAT-011
story: US-045
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-120]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-119 — User activity history model + logging

## Description

Create UserActivity model logging email changes and password changes with timestamps. Append-only per user.

## Acceptance criteria

- [ ] UserActivity model: id, user_id FK, event_type enum (email_changed/password_changed), description, old_value, new_value, created_at.
- [ ] Alembic migration creates table.
- [ ] Auto-log on email change (TODO-110) and password change (TODO-113).
- [ ] Append-only — no edit or delete (FR-11.5).
- [ ] Each entry: event type, timestamp, old/new email for email changes (FR-11.5).

## Notes

Separate from tenant-level audit trail (TODO-040). This is per-user activity.
