---
id: TODO-138
title: TenantSmtpConfig model + migration
feature: FEAT-013
story: US-053
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-139, TODO-140]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-138 — TenantSmtpConfig model + migration

## Description

Create `TenantSmtpConfig` model: one-per-tenant (unique tenant_id), fields per FR-13.1: host, port, username, password encrypted (Fernet) stored in `password_ciphertext` column, from_email, from_name, security mode enum (none/starttls/ssl), enabled bool, timestamps; alembic migration.

## Acceptance criteria

- [x] One-per-tenant model with unique tenant_id. (FR-13.1)
- [x] Fields per FR-13.1: host, port, username, from_email, from_name, security mode enum, enabled, timestamps. (FR-13.1)
- [x] Password encrypted at rest (Fernet) stored in password_ciphertext column. (FR-13.1)
- [x] Security mode enum (none/starttls/ssl). (FR-13.1)
- [x] Migration creates the table. (FR-13.1)

## Notes

- Model + migration f8a9b0c1d2e3; password Fernet-encrypted at rest (ciphertext only). (FR-13.1)
- Password never stored plaintext. (FR-13.1)
