---
id: TODO-048
title: Notes and tags UI
feature: FEAT-005
story: US-019
status: in_progress
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-048 — Notes and tags UI

## Description

Add internal notes (free-text) and simple tags/labels to client records. Notes are internal-only, never visible on Client Portal (FR-5.5).

## Acceptance criteria

- [ ] Notes field on client edit page (internal-only per FR-5.5).
- [ ] Tags input (comma-separated or chip-style) on client edit page.
- [ ] Notes/tags stored on Client model or separate table.
- [ ] Notes NEVER rendered in Client Portal views (FR-5.5).
- [ ] Filter by tag in client list (TODO-047).

## Notes

API complete (notes/tags endpoints + filter). UI in later frontend batch.

