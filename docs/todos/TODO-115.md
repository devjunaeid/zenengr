---
id: TODO-115
title: Password policy validation
feature: FEAT-011
story: US-043
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-113]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-115 — Password policy validation

## Description

Implement password policy validation (minimum length, complexity) per tenant's settings. Applies to registration, password change, and forgot-password reset.

## Acceptance criteria

- [x] Tenant password policy configurable (min_length, require_uppercase, require_numbers, require_special).
- [x] Default policy: min 8 chars.
- [x] Policy validated on: registration (TODO-027), password change (TODO-113), reset (TODO-114).
- [x] Validation error returns specific requirements message.

## Notes

Tenant setting password_min_length (default 10, validated 8-64) + shared validator in app/services/password_policy.py, wired into change-password (both realms), client register, admin reset consume.

