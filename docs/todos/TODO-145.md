---
id: TODO-145
title: Frontend settings store + tenant-aware format helpers
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-146, TODO-149, TODO-150]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-145 - Frontend settings store + tenant-aware format helpers

## Description

Create frontend settings store (runes): currency, timezone, date_format, time_format, loaded flag. Add tenant-aware format helpers `fmtPrice` (Intl currency, tenant code), `formatDate` / `formatDateTime` (date template + timezone, time per `time_format`) that read the store internally. Cache Intl formatters, rebuild only when settings change. Defaults until loaded: USD / UTC / YYYY-MM-DD / 24h.

## Acceptance criteria

- [x] Runes settings store with currency, timezone, date_format, time_format, loaded flag. (FR-14.1)
- [x] `fmtPrice` formats via Intl currency using tenant currency code. (FR-14.2)
- [x] `formatDate` / `formatDateTime` use date template + timezone; time respects `time_format`. (FR-14.2)
- [x] Helpers read the store internally - existing call sites unchanged. (FR-14.2)
- [x] Intl formatters cached, rebuilt only on settings change. (FR-14.2)
- [x] Defaults (USD / UTC / YYYY-MM-DD / 24h) until settings loaded. (FR-14.1)

## Notes

- Helpers API stable: `fmtPrice`, `formatDate`, `formatDateTime` are the only formatting entry points. (FR-14.2)
- Shipped 2026-08-05: runes settings store (currency/timezone/date_format/time_format/loaded) + cached Intl helpers fmtPrice/formatDate/formatTime/formatDateTime; defaults USD/UTC/YYYY-MM-DD/24h until loaded.
