---
id: TODO-151
title: PDF currency symbol + tests
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-148]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-151 - PDF currency symbol + tests

## Description

Prefix invoice PDF amounts with the tenant currency symbol: symbol map for common currencies + code fallback when not in map. Add tests.

## Acceptance criteria

- [x] Invoice PDF amounts prefixed with tenant currency symbol. (FR-14.7)
- [x] Fallback to currency code when symbol not in map. (FR-14.7)
- [x] Tests cover mapped currency, fallback currency, and tenant setting wiring.

## Notes

- Symbol map + code fallback per FR-14.7; depends on backend validation + `time_format`/`date_format` settings (TODO-148).
- Shipped 2026-08-05: invoice PDF money prefixed with tenant currency CODE (e.g. "BDT 500.00"); tests cover mapped currency, fallback, and tenant setting wiring.
