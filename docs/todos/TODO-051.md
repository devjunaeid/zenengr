---
id: TODO-051
title: Archive/unarchive API
feature: FEAT-005
story: US-021
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043]
blocks: [TODO-052, TODO-053]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-051 — Archive/unarchive API

## Description

Build endpoints to archive (set status to Archived) and unarchive a client. Archived clients hidden from default lists. Historical data preserved.

## Acceptance criteria

- [ ] POST /api/tenant/clients/{id}/archive sets status=Archived.
- [ ] POST /api/tenant/clients/{id}/unarchive sets status=Active.
- [ ] Archived client hidden from default active list (FR-5.8).
- [ ] All historical projects, invoices, payments remain accessible (FR-5.8).
- [ ] Archived client's users lose Client Portal access (TODO-052).
- [ ] Unarchive restores portal access.

## Notes

