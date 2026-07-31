---
id: TODO-057
title: Service catalog CRUD API + UI
feature: FEAT-006
story: US-023
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-056]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-057 — Service catalog CRUD API + UI

## Description

Build CRUD API + Admin Portal UI for service catalog management. Tenant Admin/Manager creates/edits services with milestone step templates.

## Acceptance criteria

- [x] GET/POST/PATCH/DELETE /api/tenant/services CRUD.
- [x] Service form: name, description, default price, milestone steps list.
- [x] Employee view-only (FR-4.2).
- [ ] Delete is soft if any project references the service.

## Notes

- Delete hard-deletes with FK CASCADE to step templates. Soft-delete when projects reference the service requires the Project model from FEAT-007 (TODO-062); will be added when project service-attachment lands.

