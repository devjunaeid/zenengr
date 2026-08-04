---
id: TODO-097
title: Client financial summary component
feature: FEAT-009
story: US-037
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-095]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-097 — Client financial summary component

## Description

Build client-level financial summary component aggregating across all client's projects. Used in client detail view.

## Acceptance criteria

- [x] Client detail page shows financial summary: total invoiced, total paid, total outstanding (FR-9.4).
- [x] Numbers aggregate across all projects for the client.
- [x] Optionally show per-project breakdown.
- [x] Computed from TODO-095 service.

## Notes

Client detail endpoint returns live total_invoiced/total_paid/total_outstanding via get_client_financials; existing UI cards show real numbers.

