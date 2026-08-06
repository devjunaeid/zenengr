---
id: TODO-164
title: Frontend permissions store + gating sweep
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-162]
blocks: []
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-164 - Frontend permissions store + gating sweep

## Description

Permissions store exposing `can(action, resource)`; gating sweep replaces role-name checks across staff UI.

## Acceptance criteria

- [x] Permissions store with can(action, resource). (FR-16.6)
- [x] Gating sweep: role-name checks replaced by permission checks. (FR-16.6)

## Notes

- Store backed by roles API data (permission sets per role). (FR-16.6)
- Shipped: auth.can(action, resource) store + gating sweep across staff UI; role-name checks replaced.
