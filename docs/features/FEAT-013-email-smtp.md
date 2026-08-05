---
id: FEAT-013
title: Per-Tenant Email (SMTP) & Settings Tabs
status: approved
priority: P0
source: Product decision 2026-08-05
---

# FEAT-013 — Per-Tenant Email (SMTP) & Settings Tabs

## Goal

Tenant admins configure their own SMTP for all outgoing email (invites, password reset, email verification, comment notifications); config stored in DB per tenant; settings page reorganized into top-bar tabs.

## Scope

### In Scope
- Per-tenant SMTP config stored in DB: one row per tenant: host, port, username, password (encrypted at rest — Fernet, key derived from app secret; never returned in API responses, only `has_password`), from_email, from_name, security mode enum (none/starttls/ssl), enabled bool, timestamps
- Config API (GET masked, PATCH upsert, POST test) audited; tenant-admin only (manage/settings permission)
- Async SMTP sending (aiosmtplib) supporting none/starttls/ssl; tenant-scoped factory resolves config → SMTP sender when enabled+configured, else ConsoleEmailSender (existing dev behavior)
- All email sites routed through the tenant sender: staff invites, client invites, forgot-password (admin+client), reset consumption emails, email verification, admin-triggered resets, comment notification dispatch
- Failure semantics: enabled SMTP send failure never fails the action — audit log `email.send_failed` + continue (console fallback in dev); disabled config = console fallback
- Settings tabs: `/app/settings` reorganized into top-bar tabs: Business profile (existing profile + branding/logo), Configuration (settings keys), Email (SMTP config), Plan & usage (existing plan page moved as tab)

### Out of Scope (Phase 2)
- Per-user email aliases
- DKIM/SPF management
- Templates editor
- Send history dashboard
- Queuing

## Functional Requirements

- FR-13.1: Per-tenant SMTP config stored in DB: one row per tenant: host, port, username, password (encrypted at rest — Fernet, key derived from app secret; never returned in API responses, only `has_password`), from_email, from_name, security mode enum (none/starttls/ssl), enabled bool, timestamps.
- FR-13.2: API: GET /tenant/smtp-config (masked: no password; returns has_password), PATCH /tenant/smtp-config (upsert; password optional on update — omitted keeps existing; validation: host required when enabled, port 1-65535, mode one of none/starttls/ssl, from_email valid email), audited (smtp_config.updated). Tenant-admin only (manage/settings permission).
- FR-13.3: Test connection: POST /tenant/smtp-config/test — sends a test email via configured settings (or validates connection when no recipient configured — use from_email as recipient); returns ok or error message; audited.
- FR-13.4: Sending: new SmtpEmailSender (async, aiosmtplib) supporting none/starttls/ssl; a tenant-scoped factory resolves config → SMTP sender when enabled+configured, else falls back to ConsoleEmailSender (existing dev behavior).
- FR-13.5: Routing: ALL email sites use the tenant sender: staff invites, client invites, forgot-password (admin+client), reset consumption emails, email verification, admin-triggered resets, comment notification dispatch.
- FR-13.6: Failure semantics: if tenant SMTP is enabled but a send fails, the action NEVER fails — write an audit log entry (action email.send_failed, details host/error) and continue (console fallback in dev). Disabled config = console fallback (no error logging needed).
- FR-13.7: Settings tabs: /app/settings reorganized into top-bar tabs: Business profile (existing profile + branding/logo), Configuration (settings keys), Email (SMTP config), Plan & usage (existing plan page moved as tab).

## Acceptance Criteria

1. SMTP config CRUD works per tenant (create, read masked, update, disable).
2. Password never returned in API responses — `has_password` only.
3. Password encrypted at rest (Fernet) — ciphertext in DB, never plaintext.
4. Test email sends and returns ok or error message.
5. Configured SMTP used for each email type: invites, forgot/reset, email verification, comment notifications.
6. Disabled/failed SMTP falls back without breaking the action; failure writes audit `email.send_failed`.
7. Settings tabs render and all settings modules (Business profile, Configuration, Email, Plan & usage) reachable.

## Dependencies

- FEAT-004 (User & Access Management) — staff invites + admin-triggered resets route through tenant sender
- FEAT-005 (Client Management) — client invites
- FEAT-010 (Comments / Communication) — comment notification dispatch
- FEAT-011 (Profile Management) — forgot-password (admin+client), reset consumption emails, email verification
- FEAT-012 (File Management & Storage) — branding/logo moves into Business profile tab

## Decisions

- Security modes = none/starttls/ssl selectable in UI.
- Failures logged to audit (email.send_failed) and never break the action.
- Password encrypted at rest with Fernet (key derived from app secret).
