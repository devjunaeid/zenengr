---
id: TODO-048
title: Notes and tags UI
feature: FEAT-005
story: US-019
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-048 — Notes and tags UI

## Description

Add internal notes (free-text) and simple tags/labels to client records. Notes are internal-only, never visible on Client Portal (FR-5.5).

## Acceptance criteria

- [x] Notes field on client edit page (internal-only per FR-5.5).
- [x] Tags input (comma-separated or chip-style) on client edit page.
- [x] Notes/tags stored on Client model or separate table.
- [x] Notes NEVER rendered in Client Portal views (FR-5.5).
- [x] Filter by tag in client list (TODO-047).

## Notes

Frontend batch shipped 2026-07-31. Notes section in `frontend/src/routes/app/clients/[id]/+page.svelte` (admin/manager add-note form, list, pagination). Chip-style tag input on new/edit forms (Enter or comma to add, Backspace to remove last, removable chips). Single-select tag filter on client list page. Notes not rendered in Client Portal (server-side filtering — admin realm only).

