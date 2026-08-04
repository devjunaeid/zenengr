---
id: TODO-111
title: Profile UI (Admin Portal)
feature: FEAT-011
story: US-042
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-109]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-111 — Profile UI (Admin Portal)

## Description

Build Admin Portal profile page with editable fields, email change section, and avatar upload.

## Acceptance criteria

- [x] Profile form: name, avatar, phone, timezone, language inputs.
- [x] Email display with "Change Email" button (opens TODO-110 flow).
- [x] Admin-style layout per FR-11.4.
- [x] Save button updates profile via PATCH endpoint.

## Notes

Admin profile page /app/profile: profile fields form, email change w/ pending_email banner, change password, notification prefs toggles, activity table.

