---
id: TODO-109
title: Profile edit API (both portals)
feature: FEAT-011
story: US-042
status: proposed
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

- [ ] PATCH /api/auth/profile (Admin Portal) and PATCH /api/client/auth/profile (Client Portal) update profile.
- [ ] Fields: name, avatar_url, phone, timezone, language (FR-11.1).
- [ ] User cannot change role or client association (FR-11.6).
- [ ] Email not included in this PATCH (handled by TODO-110).
- [ ] Server validates timezone and language against allowed values.

## Notes

