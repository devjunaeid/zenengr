---
id: TODO-049
title: Activity event model + logging service
feature: FEAT-005
story: US-020
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-043]
blocks: [TODO-050]
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-049 — Activity event model + logging service

## Description

Create ClientActivityEvent model for auto-logged events per client: project created, invoice issued, payment received, comment posted. Append-only.

## Acceptance criteria

- [ ] ClientActivityEvent model: id, client_id FK, event_type, description, timestamp, actor_id.
- [ ] Service method: log_client_event(client_id, event_type, description, actor_id).
- [ ] Events automatically created when project created, invoice issued, payment recorded, comment posted.
- [ ] Append-only — no edit or delete.

## Notes

Events ordered newest-first on timeline (TODO-050).
