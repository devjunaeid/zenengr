---
id: TODO-141
title: Test SMTP endpoint
feature: FEAT-013
story: US-053
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-140]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-141 — Test SMTP endpoint

## Description

POST /tenant/smtp-config/test sends a test email via configured settings (or validates connection when no recipient configured — use from_email as recipient); returns ok or error message; audited.

## Acceptance criteria

- [x] POST /tenant/smtp-config/test sends test email via configured settings. (FR-13.3)
- [x] No recipient configured → uses from_email as recipient / validates connection. (FR-13.3)
- [x] Returns ok or error message. (FR-13.3)
- [x] Audited. (FR-13.3)
- [x] Tests. (FR-13.3)

## Notes

- POST /tenant/smtp-config/test sends test email, returns ok/error; audited. (FR-13.3)
- Test connection failures surface the error; they do not affect the saved config. (FR-13.3)
