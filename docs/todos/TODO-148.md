---
id: TODO-148
title: Backend date/time format validation + defaults
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-151]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-148 - Backend date/time format validation + defaults

## Description

Restrict `date_format` to the allowed canonical set; add new `time_format` setting (12h/24h, default 24h); validate currency ISO code and IANA timezone. Centralize validation in `settings.validate_setting_value`. Add validation tests.

## Acceptance criteria

- [x] `date_format` restricted to allowed set. (FR-14.6)
- [x] New `time_format` setting, default 24h. (FR-14.6)
- [x] Currency ISO code validated; timezone IANA validated. (FR-14.5)
- [x] Validation centralized in `settings.validate_setting_value`. (FR-14.6)
- [x] Invalid values rejected with 422 in tests. (FR-14.6)

## Notes

- Canonical format set validated server-side. (FR-14.4)
- Shipped 2026-08-05: date_format validated against 12-format allowed set; time_format 12h/24h default 24h; currency 3-letter ISO + IANA timezone validated in settings.validate_setting_value; invalid values rejected with 422.
