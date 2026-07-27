---
id: TODO-030
title: Deactivate/reactivate API + UI
feature: FEAT-004
story: US-013
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-030 — Deactivate/reactivate API + UI

## Description

Build endpoints + UI for Tenant Admin to deactivate/reactivate admin users. Deactivated users lose portal access immediately. Historical records preserved.

## Acceptance criteria

- [ ] POST /api/tenant/users/{id}/deactivate sets is_active=false.
- [ ] POST /api/tenant/users/{id}/reactivate sets is_active=true.
- [ ] Deactivated user immediately loses portal access (auth middleware check).
- [ ] Historical records (comments, actions) remain attributed to deactivated user (FR-4.11).
- [ ] Last-admin guard prevents deactivating last Admin (TODO-031).
- [ ] Deactivation/reactivation audited (TODO-042).

## Notes

