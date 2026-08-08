---
id: TODO-174
title: Frontend notifications store + WS client
feature: FEAT-017
story: US-059
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-171, TODO-172]
blocks: [TODO-175]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-174 - Frontend notifications store + WS client

## Description

Runes store: unread count, list, last push. WS connect with token + reconnect/backoff; merge pushes. Used by admin + client shells.

## Acceptance criteria

- [ ] Runes store: unread count, list, last push. (FR-17.7)
- [ ] WS connect with token + reconnect/backoff. (FR-17.4, AC-5)
- [ ] Merge WS pushes (new notification + unread-count bump) into store. (FR-17.7)
- [ ] Store used by admin + client shells. (FR-17.7)

## Notes

- Client auto-reconnect with backoff (FR-17.4).
