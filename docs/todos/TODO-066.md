---
id: TODO-066
title: Milestone status UI with 4-state selector
feature: FEAT-007
story: US-026
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-065]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-066 — Milestone status UI with 4-state selector

## Description

Build milestone status selector component in project detail view. Shows current status with dropdown/button group for transition.

## Acceptance criteria

- [x] Milestone row shows current status badge.
- [x] Quick-status-change control (dropdown or button group).
- [x] Changing status calls PATCH endpoint (TODO-065).
- [x] Status badges color-coded: Pending=slate (gray), In Progress=blue, Completed=green, Blocked=red.

## Notes

