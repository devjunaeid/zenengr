---
id: TODO-050
title: Client activity timeline UI component
feature: FEAT-005
story: US-020
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-049]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-050 — Client activity timeline UI component

## Description

Build activity timeline component on Client detail page. Shows events in reverse chronological order with type icon and description.

## Acceptance criteria

- [ ] GET /api/tenant/clients/{id}/activity returns events sorted newest-first.
- [ ] Timeline UI: event type icon, timestamp, description text.
- [ ] Renders on client detail page within parent component.

## Notes

API complete (TODO-049). UI in later frontend batch.

