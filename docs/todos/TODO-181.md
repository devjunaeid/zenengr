---
id: TODO-181
title: Discount editor API
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-178]
blocks: [TODO-184]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-181 - Discount editor API

## Description

PATCH /tenant/projects/{id}/discount {type, value} (admin/manager, audited with old/new; clears via null). GET returns current discount. Single active discount: setting a new one replaces the old; NO reason note.

## Acceptance criteria

- [x] PATCH /tenant/projects/{id}/discount: admin/manager, replaces single active discount, clears via null. (FR-18.3)
- [x] Audit trail records old/new discount; no reason note. (FR-18.3)
- [x] GET returns current discount.

## Notes

- Shipped: PATCH/GET discount endpoints, audited old/new, no reason note; discount never on client timeline.
