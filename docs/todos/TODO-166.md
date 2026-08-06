---
id: TODO-166
title: Team page role assignment
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-163]
blocks: []
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-166 - Team page role assignment

## Description

Team page role select uses roles API; includes custom roles; last-admin guard preserved.

## Acceptance criteria

- [x] Role select on Team page lists system + custom roles. (FR-16.6)
- [x] Assignment via PATCH /tenant/users/{id}/role. (FR-16.5, FR-16.6)
- [x] Last-admin guard preserved. (FR-16.5)

## Notes

- Admin role selectable but protected from privilege modification of last admin. (FR-16.3)
- Shipped: Team role assignment via role_id through roles API; custom roles listed; last-admin guard preserved.
