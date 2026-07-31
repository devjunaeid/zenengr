---
id: TODO-050
title: Client activity timeline UI component
feature: FEAT-005
story: US-020
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-049]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-050 — Client activity timeline UI component

## Description

Build activity timeline component on Client detail page. Shows events in reverse chronological order with type icon and description.

## Acceptance criteria

- [x] GET /api/tenant/clients/{id}/activity returns events sorted newest-first.
- [x] Timeline UI: event type icon, timestamp, description text.
- [x] Renders on client detail page within parent component.

## Notes

Frontend batch shipped 2026-07-31. Activity section in `frontend/src/routes/app/clients/[id]/+page.svelte`: vertical timeline rendering timestamp + action + entity_type/actor_type, paginated via existing `<Pagination>` component. `frontend/src/lib/api/clients.js` exports `listActivity` calling `GET /tenant/clients/{id}/activity`.

