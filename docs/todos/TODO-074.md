---
id: TODO-074
title: Client Portal project overview
feature: FEAT-007
story: US-029
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-072, TODO-038]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-074 — Client Portal project overview

## Description

Build Client Portal project overview showing same data as Admin Portal but with client-appropriate presentation. Same data, scoped to client's view.

## Acceptance criteria

- [x] Client Portal project page shows milestone progress + financial summary.
- [x] Same GET /api/tenant/projects/{id}/overview endpoint (auth middleware scopes to client).
- [x] Client-appropriate layout per FR-7.5 AC-8.
- [x] Client User cannot see other clients' projects (FR-4.8).

## Notes

Client Portal project list + detail pages with progress, services, milestones, financial summary, linked invoices, comment thread (client realm).

