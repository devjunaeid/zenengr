---
id: TODO-109
title: Profile edit API (both portals)
feature: FEAT-011
story: US-042
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-110, TODO-111, TODO-112]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-109 — Profile edit API (both portals)

## Description

Build profile edit endpoints for both portals. Fields: name, avatar URL, phone, timezone, language. Email change has separate re-verification flow (TODO-110).

## Acceptance criteria

- [x] PATCH /api/auth/profile (Admin Portal) and PATCH /api/client/auth/profile (Client Portal) update profile.
- [x] Fields: name, avatar_url, phone, timezone, language (FR-11.1).
- [x] User cannot change role or client association (FR-11.6).
- [x] Email not included in this PATCH (handled by TODO-110).
- [x] Server validates timezone and language against allowed values.

## Notes

Profile columns (avatar_url/phone/timezone/language) on AdminUser + ClientUser + migration a1b2c3d4e5f6. Admin PATCH /api/v1/auth/profile, client PATCH /api/v1/client/auth/user-profile (distinct from client-entity profile), /me responses extended. No role/client changes possible (extra=forbid). Email change deferred to TODO-110.

Email change now live via pending_email + EmailVerificationToken + public verify endpoints (both portals); old email active until verified; duplicate email 409.

