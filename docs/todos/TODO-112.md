---
id: TODO-112
title: Profile UI (Client Portal)
feature: FEAT-011
story: US-042
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-109, TODO-038]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-112 — Profile UI (Client Portal)

## Description

Build Client Portal profile page with same fields as Admin Portal but Client-style layout per FR-11.4.

## Acceptance criteria

- [x] Client Portal profile page: same editable fields as Admin Portal.
- [x] Client-style layout per FR-11.4.
- [x] Email change flow (TODO-110) accessible.
- [x] User cannot change role or client association (FR-11.6).

## Notes

Client profile page gains Your account section (profile fields, password, prefs, activity) via /client/auth/user-profile + account APIs.

