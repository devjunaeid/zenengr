---
id: FEAT-017
title: Realtime Notifications (Admin + Client)
status: proposed
priority: P0
source: Product decision 2026-08-06
---

# FEAT-017 - Realtime Notifications (Admin + Client)

## Goal

Deliver realtime, permission-scoped, in-app notifications in both portals (Admin + Client): business events produce a Notification row and a live WebSocket push to the users who are allowed to see them. Staff recipients are filtered by their effective permissions for the event's module (FEAT-016 grants; super_admin/tenant-admin bypass); client recipients are the client users of the relevant client, scoped to their own client's projects/invoices. Cross-tenant visibility is impossible. Client portal mirrors admin activity for its own data (invoice issued, payment received, milestone completed, shared comment).

## Functional Requirements

- FR-17.1: Event enum expansion + preference channels. `NotificationEventType` gains `refund_recorded`, `advance_applied`, `project_created` alongside existing `new_comment`, `invoice_issued`, `payment_received`, `milestone_completed`. `NotificationPreference` gains a `channel` dimension (`email` | `inapp`): existing rows backfilled as `email`; in-app preferences are get-or-create with default enabled; per-event toggles are independent for email vs in-app.
- FR-17.2: Notification model. `Notification {id, user_id, user_type, tenant_id, event_type, title, body, entity_type, entity_id, data JSONB, is_read, created_at}`. History retained (rows never deleted); read state tracked per user.
- FR-17.3: Recipient resolution with permission scoping + client mirror. Notification service resolves staff recipients by effective permission for the event's module (effective_permissions per user from FEAT-016; super_admin/admin bypass); client recipients = client users of the relevant client (project/invoice), scoped to their own projects only; cross-tenant impossible. In-app delivery filtered by in-app preference channel.
- FR-17.4: WebSocket transport. Endpoints `/ws/admin` and `/ws/client`, token auth via query param. ConnectionManager tracks `user_id -> set[websocket]` per realm (admin/client). New notifications are pushed to connected sockets plus an unread-count bump; client auto-reconnects with backoff.
- FR-17.5: REST API. Staff: GET /tenant/notifications (paginated), GET unread-count, POST mark-read, POST mark-all-read. Client: GET /client/notifications + equivalents. WS pushes new notifications + unread-count bumps.
- FR-17.6: Preferences with email/in-app channels. Notification prefs API + service support both channels; in-app get-or-create default enabled; per-event toggles independent for email vs in-app.
- FR-17.7: Frontend bell/badge/panel. Notifications store + WS client (admin + client), bell with unread badge, dropdown panel (list, mark read, mark all, link to entity); preferences UI split into Email vs In-app toggle sections.

## Acceptance Criteria

1. GET /tenant/notifications returns the current user's notifications paginated, tenant + user scoped; GET unread-count, POST mark-read, POST mark-all-read work; /client/notifications equivalents work in the client realm.
2. A notification row is created for every supported business event; history retained; read state per user.
3. Staff receive a notification only for events they have effective permission to see; no notification for modules without permission; super_admin/tenant-admin bypass.
4. Client users receive notifications only for their own client's projects/invoices (invoice issued, payment received, milestone completed, shared comment); never other clients' data.
5. WS: `/ws/admin` and `/ws/client` authenticate via token query param; new notifications + unread-count bumps arrive in realtime; client auto-reconnects.
6. In-app preferences default enabled (get-or-create); disabling an event for in-app stops in-app delivery for that event only; email toggle independent.
7. Frontend: bell with unread badge in both portals; dropdown panel lists notifications (unread marked), supports mark-read + mark-all, links to the entity page; badge updates in realtime.
8. Cross-tenant notification delivery is impossible (tenant_id always matches recipient tenant).

## Out of Scope (Phase 2)

- Push notifications (APNS / FCM / web-push)
- Notification center deep-linking beyond entity pages
- Read receipts
- Dedup / batching

## Dependencies

- FEAT-016 (Custom Roles & Permission Management) - effective_permissions used for staff recipient scoping
- FEAT-010 (Comments / Communication) - comment events + existing email dispatch service
- FEAT-008/009 (Invoicing / Payments) - invoice/payment/refund/advance events
- FEAT-007 (Project Management) - milestone + project events
- FEAT-011 (Profile Management) - NotificationPreference model extended with channel dimension

## Decisions

- Realtime transport: WebSocket endpoints /ws/admin + /ws/client, token auth via query param, auto-reconnect on client.
- Notification history is DB-backed (Notification table); read state per user; history retained.
- Fan-out is permission-filtered: staff recipients resolved by effective permissions for the event's module (FEAT-016 grants; super_admin/admin bypass); client recipients = client users of the relevant client (project/invoice), scoped to their own client; cross-tenant impossible.
- Client mirror: invoice issued, payment received, milestone completed, shared comment notify the project's client users (their own projects only).
- Preferences: NotificationPreference gains a `channel` dimension (email | inapp); existing rows backfilled as email; in-app get-or-create default enabled; per-event toggles independent for email vs in-app.
- Architecture: WS + DB-backed history + permission-filtered fan-out; out of scope for Phase 2: push, deep-linking beyond entity pages, read receipts, dedup/batching.
