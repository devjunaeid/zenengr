---
id: TODO-170
title: "Notification service: create + permission-scoped recipients"
feature: FEAT-017
story: US-059
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-169]
blocks: [TODO-171, TODO-173]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-170 - Notification service: create + permission-scoped recipients

## Description

Notification service: `create_notification(session, *, tenant_id, event_type, title, body, entity_type, entity_id, data, target_users or resolver)`. Recipient resolution helpers: staff with permission for the event's module (effective_permissions per user; super_admin/admin bypass); client mirror (client users of the relevant client, their own projects only). In-app channel preference filtering. Tests.

## Acceptance criteria

- [ ] create_notification(session, *, tenant_id, event_type, title, body, entity_type, entity_id, data, target_users or resolver). (FR-17.3)
- [ ] Staff recipients filtered by effective permission for the event's module (FEAT-016 grants; super_admin/admin bypass). (FR-17.3, AC-3)
- [ ] Client mirror: client users of client_id, their own projects only. (FR-17.3, AC-4)
- [ ] In-app channel preference filtering (get-or-create default enabled; disabled skips). (FR-17.6, AC-6)
- [ ] Cross-tenant impossible (tenant_id always recipient's tenant). (AC-8)
- [ ] Tests: staff permission scoping, admin bypass, client mirror scoping, pref filtering, cross-tenant guard.

## Notes

- Staff + client recipient resolution helpers reusable by event producers (TODO-173).
