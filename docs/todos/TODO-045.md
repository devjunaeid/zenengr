---
id: TODO-045
title: Client detail view with contacts
feature: FEAT-005
story: US-018
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-045 — Client detail view with contacts

## Description

Build client detail page showing full client info plus list of associated Client Users/contacts with primary billing contact indicator.

## Acceptance criteria

- [x] GET /api/tenant/clients/{id} returns client with contacts array.
- [x] Detail page: client info + contacts section.
- [x] Primary billing contact highlighted.
- [x] Employee view-only; Admin/Manager can edit.

## Notes

Frontend batch shipped 2026-07-31. `frontend/src/routes/app/clients/[id]/+page.svelte` renders profile + financials + contacts sections; "Primary billing contact" badge applied where `is_primary_billing_contact: true`. `frontend/src/routes/app/clients/[id]/+page.js` loads client + notes + activity in parallel. Employee view-only banner via `isEmployee` flag.

