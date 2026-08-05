---
id: TODO-140
title: SMTP config CRUD API
feature: FEAT-013
story: US-053
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-138, TODO-139]
blocks: [TODO-141, TODO-144]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-140 — SMTP config CRUD API

## Description

GET /tenant/smtp-config (masked: no password; returns has_password), PATCH /tenant/smtp-config (upsert; password optional on update — omitted keeps existing; validation: host required when enabled, port 1-65535, mode one of none/starttls/ssl, from_email valid email), audited (smtp_config.updated). Tenant-admin only (manage/settings permission).

## Acceptance criteria

- [x] GET returns masked config: no password, has_password only. (FR-13.2)
- [x] PATCH upserts config; password omitted on update keeps existing. (FR-13.2)
- [x] Validation: host required when enabled, port 1-65535, mode one of none/starttls/ssl, from_email valid email. (FR-13.2)
- [x] Audited (smtp_config.updated). (FR-13.2)
- [x] Tenant-admin only (manage/settings permission). (FR-13.2)
- [x] Tests: masking, keep-password-on-omit, validation. (FR-13.2)

## Notes

- GET/PATCH /tenant/smtp-config: masked (has_password only), upsert keeps password when omitted, audited. (FR-13.2)
- Password never returned in API responses. (FR-13.1)
