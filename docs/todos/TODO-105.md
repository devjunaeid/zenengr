---
id: TODO-105
title: Internal comment visual indicator
feature: FEAT-010
story: US-040
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-103]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-105 — Internal comment visual indicator

## Description

Add visual badge/icon to internal-only comments in Admin Portal thread. Distinguish them visually from shared comments.

## Acceptance criteria

- [x] Internal comments show "Internal" badge (red/orange).
- [x] Badge visible only in Admin Portal (Client Portal never sees these comments).
- [x] Shared comments have no badge.

## Notes

Internal comments show red Internal pill; visible only to staff (client realm never receives internal comments - server-filtered).

