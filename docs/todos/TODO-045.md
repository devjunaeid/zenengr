---
id: TODO-045
title: Client detail view with contacts
feature: FEAT-005
story: US-018
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-045 — Client detail view with contacts

## Description

Build client detail page showing full client info plus list of associated Client Users/contacts with primary billing contact indicator.

## Acceptance criteria

- [ ] GET /api/tenant/clients/{id} returns client with contacts array.
- [ ] Detail page: client info + contacts section.
- [ ] Primary billing contact highlighted.
- [ ] Employee view-only; Admin/Manager can edit.

## Notes

API complete (TODO-043). UI in later frontend batch.

