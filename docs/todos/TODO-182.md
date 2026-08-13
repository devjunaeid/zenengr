---
id: TODO-182
title: Project ledger API (staff + client)
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-180]
blocks: [TODO-183]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-182 - Project ledger API (staff + client)

## Description

GET /tenant/projects/{id}/ledger + GET /client/projects/{id}/ledger (client-scoped to own client's projects). Response {entries, summary}. Cross-tenant/cross-client access impossible.

## Acceptance criteria

- [x] GET /tenant/projects/{id}/ledger returns {entries, summary}. (FR-18.4)
- [x] GET /client/projects/{id}/ledger client-scoped (own projects only); cross-tenant impossible. (FR-18.9)

## Notes

- Shipped: staff + client-scoped ledger APIs returning {entries, summary}.
