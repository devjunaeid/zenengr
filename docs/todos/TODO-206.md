---
id: TODO-206
story: US-069
feature: FEAT-023
title: Backend support for number_system tenant setting and validation
status: done
priority: P1
dependencies: []
blocks: [TODO-207, TODO-208]
---

# TODO-206 - Backend support for number_system tenant setting and validation

## What to do

1. Edit `backend/app/services/settings.py`:
   - Add `number_system` to `DEFAULT_SETTINGS` with default value `"international"` and permission `PermissionLevel.TENANT_ADMIN_EDITABLE`.
   - Update `validate_setting_value`: ensure `number_system` is one of `("international", "south_asian", "indian")`.
   - Add `"number_system"` to `CLIENT_FORMATTING_KEYS`.
2. Add backend tests verifying `number_system` retrieval, validation, and update.

## Acceptance Check

- `GET /api/v1/tenant/settings` returns `number_system` item.
- Updating `number_system` with invalid string raises 422.
- Updating with `"south_asian"` or `"international"` succeeds.
- Targeted tests pass cleanly.
