---
id: TODO-176
title: Frontend in-app preference toggles
feature: FEAT-017
story: US-059
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-168]
blocks: [TODO-177]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-176 - Frontend in-app preference toggles

## Description

Settings/profile prefs UI split into Email + In-app sections: channel-aware toggles per event type. In-app section added alongside existing email prefs (FEAT-011).

## Acceptance criteria

- [x] Prefs UI split into Email + In-app sections. (FR-17.6, AC-6)
- [x] Channel-aware toggles per event type (new_comment, invoice_issued, payment_received, milestone_completed, refund_recorded, advance_applied, project_created). (FR-17.6, AC-6)
- [x] Toggling in-app does not affect email and vice versa. (FR-17.6, AC-6)

## Notes

- Extends existing notification prefs UI (TODO-116/117) with the channel dimension.
- Shipped: prefs UI split into Email + In-app sections; channel-aware toggles per event type; toggling in-app independent of email and vice versa.
