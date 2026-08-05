---
id: TODO-139
title: SMTP sender + tenant email factory
feature: FEAT-013
story: US-053
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-138]
blocks: [TODO-140, TODO-142]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-139 — SMTP sender + tenant email factory

## Description

`SmtpEmailSender` (async, aiosmtplib) supporting none/starttls/ssl; encryption helpers (encrypt/decrypt password with Fernet key from settings); `get_sender_for_tenant(session, tenant_id)` returns SMTP sender if enabled+configured else ConsoleEmailSender (existing dev behavior).

## Acceptance criteria

- [x] SmtpEmailSender (async, aiosmtplib) supporting none/starttls/ssl. (FR-13.4)
- [x] Encryption helpers (encrypt/decrypt) with Fernet key from settings. (FR-13.1)
- [x] get_sender_for_tenant(session, tenant_id) → SMTP sender if enabled+configured else console. (FR-13.4)
- [x] Unit tests incl. encryption roundtrip. (FR-13.4)

## Notes

- SmtpEmailSender (aiosmtplib) + tenant sender factory with console fallback; encryption roundtrip tests green. (FR-13.4)
- Fernet key derived from app secret. (FR-13.1)
- Disabled config = console fallback (no error logging needed). (FR-13.6)
