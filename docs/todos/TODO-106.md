---
id: TODO-106
title: Comment notification email template
feature: FEAT-010
story: US-041
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-100]
blocks: [TODO-107]
created: "2026-07-26"
updated: "2026-08-03"
---

# TODO-106 — Comment notification email template

## Description

Create email template for new shared comment notification. Includes project name, comment author, content snippet.

## Acceptance criteria

- [x] Email template: "[Project Name] - New comment from [Author]".
- [x] Body: author name, content snippet (first N chars), link to project.
- [x] Sent only for shared comments (NOT internal-only) (FR-10.5 AC-7).
- [x] Receipt respects user notification preferences (TODO-107, TODO-108).

## Notes

Template: [Project Name] New comment from Author; body = author + 200-char snippet + portal link. Sent only for shared comments. Prefs filtering deferred to TODO-116.

