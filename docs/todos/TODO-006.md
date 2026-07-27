---
id: TODO-006
title: Slug validation and uniqueness logic
feature: FEAT-001
story: US-004
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-006 — Slug validation and uniqueness logic

## Description

Implement slug format validation (lowercase alphanumeric + hyphens, no leading/trailing hyphen) with real-time uniqueness check. Slug used for subdomain or login routing per FR-1.2.

## Acceptance criteria

- [ ] Slug regex validation: ^[a-z0-9]+(-[a-z0-9]+)*$.
- [ ] Real-time availability check endpoint for UI.
- [ ] Slug immutable after creation (US-004 Notes).
- [ ] Unique constraint at DB level (TODO-004).

## Notes

