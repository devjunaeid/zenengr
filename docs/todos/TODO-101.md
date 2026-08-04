---
id: TODO-101
title: Comment thread UI component
feature: FEAT-010
story: US-039
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-100]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-101 — Comment thread UI component

## Description

Build reusable comment thread component: list of comments with author avatar, name, timestamp, content, and internal-only badge. New comment form at bottom.

## Acceptance criteria

- [x] Comment list: sorted oldest-first.
- [x] Each comment: author name + avatar, author type badge, timestamp, content.
- [x] Internal-only comments show badge (TODO-105).
- [x] New comment text area + submit button.
- [x] Optimistic UI update on new comment.

## Notes

CommentThread.svelte: self-fetching, realm-aware (admin/client), post form, internal-only toggle for staff, author chips, internal red badge, empty/error states.

