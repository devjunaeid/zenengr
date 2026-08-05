---
id: TODO-136
title: Quota enforcement + limits tests
feature: FEAT-012
story: US-052
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-128]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-136 — Quota enforcement + limits tests

## Description

Tests for quota and limits: 25MB per-file cap, tenant quota from plan `max_storage_mb`, 413 paths, boundary behavior (sum of stored sizes + new upload <= quota allowed), live-sum quota check.

## Acceptance criteria

- [x] Test: file over 25MB rejected (413). (FR-12.7)
- [x] Test: tenant over plan `max_storage_mb` rejected (413 with message). (FR-12.7)
- [x] Test: quota boundary (sum == quota allowed). (FR-12.7)
- [x] Test: quota check uses live sum of stored sizes. (FR-12.7)

## Notes

- Backend tests in `backend/tests/` per `docs/backend-standard.md`.
- Quota + 25MB cap + size tests green.
