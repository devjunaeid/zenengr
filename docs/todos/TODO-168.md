---
id: TODO-168
title: Event enum expansion + preference channels (email/inapp)
feature: FEAT-017
story: US-059
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-169, TODO-176]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-168 - Event enum expansion + preference channels (email/inapp)

## Description

Expand `NotificationEventType` with `refund_recorded`, `advance_applied`, `project_created` (alongside existing new_comment, invoice_issued, payment_received, milestone_completed). Add `channel` dimension to NotificationPreference (`email` | `inapp`): migration backfills existing rows as email; in-app get-or-create default enabled; prefs API + service support both channels with independent per-event toggles.

## Acceptance criteria

- [x] NotificationEventType += refund_recorded, advance_applied, project_created. (FR-17.1)
- [x] NotificationPreference.channel column (email|inapp) + migration backfilling existing rows as email. (FR-17.1)
- [x] Prefs API + service support both channels; in-app get-or-create default enabled. (FR-17.6)
- [x] Per-event toggles independent for email vs in-app. (FR-17.6)
- [x] Tests: enum values, channel backfill, get-or-create defaults, independent toggles.

## Notes

- Existing enum (backend/app/models/enums.py) has 4 values; adds 3.
- Existing NotificationPreference model is polymorphic (user_id, user_type, tenant_id, event_type, enabled) - channel added without breaking email dispatch.
- Shipped: NotificationEventType += refund_recorded/advance_applied/project_created; NotificationPreference channel (email|inapp) + migration h4a5b6c7d8e9; prefs API + service support both channels; independent per-event toggles.
