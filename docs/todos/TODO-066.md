---
id: TODO-066
title: Milestone status UI with 4-state selector
feature: FEAT-007
story: US-026
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-065]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-066 — Milestone status UI with 4-state selector

## Description

Build milestone status selector component in project detail view. Shows current status with dropdown/button group for transition.

## Acceptance criteria

- [ ] Milestone row shows current status badge.
- [ ] Quick-status-change control (dropdown or button group).
- [ ] Changing status calls PATCH endpoint (TODO-065).
- [ ] Status badges color-coded: Pending=gray, In Progress=blue, Completed=green, Blocked=red.

## Notes

