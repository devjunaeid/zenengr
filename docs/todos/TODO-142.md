---
id: TODO-142
title: Route email sites through tenant sender
feature: FEAT-013
story: US-053
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-139]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-142 — Route email sites through tenant sender

## Description

Route all email sites through the tenant sender resolved via `get_sender_for_tenant`: staff invites, client invites, forgot-password (admin+client), reset consumption emails, email verification, admin-triggered resets, comment notification dispatch. Failure → audit email.send_failed + console fallback; action never breaks.

## Acceptance criteria

- [x] Staff + client invites resolve sender via tenant factory. (FR-13.5)
- [x] Forgot/reset (admin+client) + email verification use tenant sender. (FR-13.5)
- [x] Admin-triggered resets use tenant sender. (FR-13.5)
- [x] Comment notification dispatch uses tenant sender. (FR-13.5)
- [x] Send failure → audit email.send_failed + console fallback; action never breaks. (FR-13.6)
- [x] Tests for at least comment dispatch + invite. (FR-13.6)

## Notes

- All email sites (invites, forgot/reset, verification, admin resets, comment notifications) route via tenant sender; failure → audit email.send_failed, action never breaks. (FR-13.5, FR-13.6)
- Failure semantics per FR-13.6: never fail the action.
