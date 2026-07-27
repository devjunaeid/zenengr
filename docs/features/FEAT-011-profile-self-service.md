---
id: FEAT-011
title: Profile Management (Self-Service)
status: approved
priority: P0
source: docs/prd.md §6.11
---

# FEAT-011 — Profile Management (Self-Service)

## Goal

Let every logged-in user (both Admin Portal and Client Portal) view and edit their own profile: name, avatar, email, phone, timezone, language preference. Support password changes with current-password confirmation and forgot-password flow. Notification preferences per user. No privilege escalation via profile edits.

## Scope

### In Scope
- Profile view/edit: name, avatar, email (re-verification on change), phone, timezone, language preference
- Password change (current-password confirmation) and forgot-password flow
- Notification preferences per user (email on: new comment, invoice issued, payment received, milestone completed)
- Separate profile UIs for Admin Portal and Client Portal (same principle: own record only)
- Activity history for email/password changes

### Out of Scope
- Profile editing for other users (admin management is in FEAT-004)
- Privilege escalation via profile fields (role or client association not editable)
- Avatar upload/storage (Phase 2 candidate; simple URL in MVP)

## Functional Requirements

- FR-11.1: Every logged-in user (either portal) can view/edit own profile: name, avatar, email (re-verification on change), phone, timezone, language preference (single default OK for MVP).
- FR-11.2: Every logged-in user can change own password (current-password confirmation) and trigger a "forgot password" flow via email.
- FR-11.3: Every logged-in user can set **notification preferences** (email on: new comment, invoice issued, payment received, milestone completed) — default on, user-adjustable.
- FR-11.4: Admin-side and Client-side profile screens are visually/functionally separate but share the principle: a user only ever edits their *own* record.
- FR-11.5: Changing own email/password requires no Tenant Admin involvement, but appears in the account's own activity history (e.g., "Password changed on [date]").
- FR-11.6: Profile changes must not allow privilege escalation (Client User cannot change role or Client association; Employee cannot self-promote).

## Acceptance Criteria

1. Any logged-in user can view and edit their own profile fields.
2. Changing email triggers re-verification flow; old email remains active until new one is verified.
3. Password change requires current password; incorrect current password rejects the change.
4. Forgot-password flow sends a reset link to the user's email.
5. Notification preferences page shows toggles for each event type; defaults are all enabled.
6. Disabling an event type stops email notifications for that event.
7. Admin Portal user sees Admin-style profile UI; Client Portal user sees Client-style profile UI.
8. Client User cannot change their role or client association via profile edit.
9. Employee cannot promote themselves to Manager or Admin via profile edit.
10. Email/password changes are logged in the user's activity history.

## Dependencies

- FEAT-001 (Tenant Management) — users are tenant-scoped
- FEAT-004 (User & Access Management) — user records and auth realms

## Decisions

- **Both portals, own-record only, no privilege escalation via profile edits.**
