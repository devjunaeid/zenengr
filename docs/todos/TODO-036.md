---
id: TODO-036
title: Permission matrix test coverage
feature: FEAT-004
story: US-015
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-034]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-036 — Permission matrix test coverage

## Description

Write comprehensive tests for permission matrix: every role x action x resource combination per FR-4.2.

## Acceptance criteria

- [ ] Test every role: Admin, Manager, Employee against every resource action.
- [ ] Tests verify allowed actions succeed and denied actions return 403.
- [ ] Test Super Admin vs tenant role separation.
- [ ] Test role change effect on next request.

## Notes

