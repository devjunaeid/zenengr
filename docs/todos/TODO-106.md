---
id: TODO-106
title: Comment notification email template
feature: FEAT-010
story: US-041
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-100]
blocks: [TODO-107]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-106 — Comment notification email template

## Description

Create email template for new shared comment notification. Includes project name, comment author, content snippet.

## Acceptance criteria

- [ ] Email template: "[Project Name] - New comment from [Author]".
- [ ] Body: author name, content snippet (first N chars), link to project.
- [ ] Sent only for shared comments (NOT internal-only) (FR-10.5 AC-7).
- [ ] Receipt respects user notification preferences (TODO-107, TODO-108).

## Notes

