---
id: TODO-149
title: Sweep call sites to helpers
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-145]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-149 - Sweep call sites to helpers

## Description

Replace raw `toLocaleString` / Intl date usages across staff + client routes with the format helpers: files, invoices (dates/prices), projects, activity, audit log, comments, settings, client portal.

## Acceptance criteria

- [x] No raw `toLocaleString` / Intl date/price formatting left in staff routes. (FR-14.3)
- [x] No raw `toLocaleString` / Intl date/price formatting left in client portal routes. (FR-14.3)
- [x] Files, invoices, projects, activity, audit log, comments, settings all use helpers. (FR-14.3)

## Notes

- Helpers read the store internally, so call sites only swap to `fmtPrice` / `formatDate` / `formatDateTime`. (FR-14.2)
- Shipped 2026-08-05: sweep complete - raw toLocaleString / Intl date+price formatting replaced with helpers across staff + client routes; date-only values tz-neutral.
