---
id: TODO-167
title: Tests + verification + docs sync
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-161, TODO-162, TODO-163, TODO-164, TODO-165, TODO-166]
blocks: []
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-167 - Tests + verification + docs sync

## Description

End-to-end tests: catalog endpoint, system role seeding + user migration, tenant-admin bypass, custom role CRUD + guards (409 on assigned delete, protected roles), reset-defaults, role assignment + last-admin guard, cache invalidation, audit entries. Full suite green. Sync docs (stories/todos status, progress).

## Acceptance criteria

- [x] Tests: catalog + seeding/migration. (FR-16.2, FR-16.5)
- [x] Tests: tenant-admin bypass + DB-grant enforcement + cache invalidation. (FR-16.4)
- [x] Tests: custom role CRUD, delete guards (409, protected roles), reset-defaults. (FR-16.5)
- [x] Tests: role assignment + last-admin guard. (FR-16.5)
- [x] Tests: audit entries for role + assignment actions. (FR-16.5)
- [x] Full suite green; docs synced.

## Notes

- Backend checks (ruff, mypy, pytest) run from backend/ against containerized stack. (FR-16.7)
- Shipped: 602 backend tests green; frontend check/lint/build clean; verified live (Roles page + employee toggles).
