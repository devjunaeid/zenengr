---
id: TODO-102
title: Comment thread in Admin Portal
feature: FEAT-010
story: US-039
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-100]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-102 — Comment thread in Admin Portal

## Description

Integrate comment thread component into Admin Portal project detail page.

## Acceptance criteria

- [ ] Project detail page has "Comments" section/tab.
- [ ] GET /api/tenant/projects/{id}/comments returns comments (with internal comments for tenant staff).
- [ ] Tenant staff can post and see all comments (including internal-only).
- [ ] Client Users cannot see internal-only comments (visibility enforced server-side).

## Notes

