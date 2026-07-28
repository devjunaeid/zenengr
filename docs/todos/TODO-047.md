---
id: TODO-047
title: Search/filter implementation
feature: FEAT-005
story: US-019
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-046]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-047 — Search/filter implementation

## Description

Add search by name and filter by status, tag, outstanding balance range to client list endpoint.

## Acceptance criteria

- [ ] Query param: ?search=term filters by name substring.
- [ ] Query param: ?status=Active|Archived filters by status.
- [ ] Query param: ?tag=tagname filters by tag.
- [ ] Query param: ?min_balance&max_balance filters by outstanding range.
- [ ] Combined filters work together.

## Notes

