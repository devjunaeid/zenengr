---
id: TODO-177
title: Tests + verification + docs sync
feature: FEAT-017
story: US-059
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-168, TODO-169, TODO-170, TODO-171, TODO-172, TODO-173, TODO-174, TODO-175, TODO-176]
blocks: []
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-177 - Tests + verification + docs sync

## Description

End-to-end tests: event enum expansion + channel backfill, Notification model + indexes, recipient resolution (staff permission scoping, admin bypass, client mirror, cross-tenant guard), WS auth + fan-out, REST API (list/unread/mark-read/mark-all both realms), per-hook event producers, frontend store/WS/bell. Full suite green. Sync docs (stories/todos status, progress).

## Acceptance criteria

- [ ] Tests: enum + channel backfill + get-or-create defaults. (FR-17.1, FR-17.6)
- [ ] Tests: recipient resolution (staff permission scoping, admin bypass, client mirror, cross-tenant). (FR-17.3)
- [ ] Tests: WS auth + fan-out + realm separation. (FR-17.4)
- [ ] Tests: REST API both realms. (FR-17.5)
- [ ] Tests: per-hook event producers. (FR-17.3)
- [ ] Full suite green; docs synced.

## Notes

- Backend checks (ruff, mypy, pytest) run from backend/ against containerized stack.
- Frontend: npm run check / lint / build.
