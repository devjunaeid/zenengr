---
id: TODO-087
title: Client Portal invoice list view
feature: FEAT-008
story: US-034
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-075, TODO-038]
blocks: [TODO-088]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-087 — Client Portal invoice list view

## Description

Build Client Portal invoice list showing all invoices for the client's projects. View-only — no edit actions.

## Acceptance criteria

- [x] GET /api/client/invoices returns invoices for Client User's client.
- [x] List: invoice number, issue date, due date, amount, status, balance due (FR-8.6).
- [x] Status badges: Issued, Partially Paid, Paid, Void.
- [x] View-only — no edit, no void (FR-8.6).
- [x] Invoices from other clients invisible (FR-4.8).

## Notes

Client invoice list page (status filter, pagination, void excluded by backend).

