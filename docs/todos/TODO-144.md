---
id: TODO-144
title: SMTP settings UI
feature: FEAT-013
story: US-054
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-140, TODO-143]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-144 — SMTP settings UI

## Description

Email tab form: host, port, username, password (placeholder "unchanged" when set), from email, from name, security mode select (none/starttls/ssl), enabled toggle, Save, Send test email button with result banner; masked has_password indicator.

## Acceptance criteria

- [x] Email tab contains SMTP form. (FR-13.7)
- [x] Fields: host, port, username, password (placeholder "unchanged" when set), from email, from name. (FR-13.2)
- [x] Security mode select (none/starttls/ssl). (FR-13.1)
- [x] Enabled toggle. (FR-13.1)
- [x] Save + Send test email button with result banner. (FR-13.3)
- [x] Masked has_password indicator shown. (FR-13.2)

## Notes

- Email tab SMTP form: host/port/username/password (masked)/from/mode select/enabled + test button. (FR-13.7)
- Password never returned from API — UI relies on has_password. (FR-13.1)
