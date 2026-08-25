---
id: TODO-191
title: Frontend live statement preview & print UI on project detail page
feature: FEAT-019
story: US-063
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-188, TODO-190]
blocks: [TODO-193]
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-191 — Frontend live statement preview & print UI on project detail page

## Description

Add "Preview / Print Statement" button and modal on the Project detail page (`frontend/src/routes/app/projects/[id]/+page.svelte`):
- Displays live financial statement table (charges, payments, advance balance, net due).
- Allows downloading or printing the live statement PDF directly in browser.

## Acceptance criteria

- [ ] "Preview Statement" action on project details page.
- [ ] Real-time updates when services or payments change.
- [ ] Downloadable live PDF preview.
