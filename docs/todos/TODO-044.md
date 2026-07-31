---
id: TODO-044
title: Client create/edit UI
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

# TODO-044 — Client create/edit UI

## Description

Build client create and edit form in Admin Portal. Fields: name, contact info, billing address, tax ID, status.

## Acceptance criteria

- [x] Create client form with all fields per FR-5.1.
- [x] Edit client form pre-populates existing data.
- [ ] Status select: Active/Archived (FR-5.2).
- [x] Employee role sees form as read-only (FR-4.2).

## Notes

Frontend batch shipped 2026-07-31. `frontend/src/routes/app/clients/new/+page.svelte` (create form) + `frontend/src/routes/app/clients/[id]/edit/+page.svelte` (edit form, pre-populated). `frontend/src/lib/api/clients.js` exports `createClient` + `updateClient`. Employee read-only enforced via `isEmployee` banner + form-level disable. Status field intentionally omitted from forms — backend schema treats `status` as immutable; archive/unarchive use dedicated endpoints (`archiveClient` / `unarchiveClient`) wired in detail page. AC3 (Status select) not met by design.

