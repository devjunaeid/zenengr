---
id: TODO-192
title: Frontend 'Generate Statement Invoice' action & Client portal statement view
feature: FEAT-019
story: US-064
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-189, TODO-190]
blocks: [TODO-193]
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-192 — Frontend 'Generate Statement Invoice' action & Client portal statement view

## Description

- Add "Generate Statement Invoice" button on the Project details page (with confirmation dialog showing the entries to be invoiced and resulting due/advance).
- Update Invoice detail pages in both Staff (`/app/invoices/[id]`) and Client Portal (`/client/invoices/[id]`) to render the statement breakdown (services + payments + advance credit + due amount).

## Acceptance criteria

- [ ] One-click "Generate Statement Invoice" button with live preview confirmation.
- [ ] Issued statement invoice renders properly in staff invoice view.
- [ ] Client portal displays statement details and PDF download.
