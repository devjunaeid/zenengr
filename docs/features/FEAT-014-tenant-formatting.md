---
id: FEAT-014
title: Tenant-Wide Formatting (Currency / Timezone / Date & Time)
status: approved
priority: P0
source: Product decision 2026-08-05
---

# FEAT-014 - Tenant-Wide Formatting (Currency / Timezone / Date & Time)

## Goal

Tenant settings (currency, timezone, date format, time format) are applied GLOBALLY across both portals (staff + client) - changing a setting reflects everywhere immediately.

## Scope

### In Scope
- Single source of truth: frontend settings store populated once per session from `GET /tenant/settings` (staff) + new `GET /client/settings` (client portal, same 4 formatting keys, no permission internals); defaults until loaded (USD / UTC / YYYY-MM-DD / 24h)
- Central formatting helpers: `fmtPrice` (Intl currency, tenant code), `formatDate` / `formatDateTime` (date template + timezone, time per `time_format`); helpers read the store internally so existing call sites are unchanged; Intl formatters cached and rebuilt only when settings change (efficiency)
- Applied everywhere: files, invoices (dates/prices), projects, activity, audit log, comments, settings, client portal
- Date format dropdown in Settings -> Configuration with live demo labels (e.g. "YYYY-MM-DD - 2026-08-05"); canonical format set validated server-side
- Time format dropdown (12h/24h); currency ISO code text (validated); timezone IANA text (validated)
- Backend: `date_format` restricted to allowed set; new `time_format` setting (default 24h); validation centralized in `settings.validate_setting_value`
- Invoice PDF amounts prefixed with tenant currency symbol (map + code fallback)

### Out of Scope (Phase 2)
- Per-user locale overrides
- Multi-currency invoices
- i18n translations

## Functional Requirements

- FR-14.1: Frontend settings store populated once per session from `GET /tenant/settings` (staff) + new `GET /client/settings` (client portal, same 4 formatting keys, no permission internals); defaults until loaded (USD / UTC / YYYY-MM-DD / 24h).
- FR-14.2: Central formatting helpers: `fmtPrice` (Intl currency, tenant code), `formatDate` / `formatDateTime` (date template + timezone, time per `time_format`); helpers read the store internally so existing call sites are unchanged; Intl formatters cached and rebuilt only when settings change (efficiency).
- FR-14.3: Helpers applied everywhere: files, invoices (dates/prices), projects, activity, audit log, comments, settings, client portal.
- FR-14.4: Date format is a dropdown in Settings -> Configuration with live demo labels (e.g. "YYYY-MM-DD - 2026-08-05"); canonical format set validated server-side.
- FR-14.5: Time format dropdown (12h/24h); currency ISO code text (validated); timezone IANA text (validated).
- FR-14.6: Backend: `date_format` restricted to allowed set; new `time_format` setting (default 24h); validation centralized in `settings.validate_setting_value`.
- FR-14.7: Invoice PDF amounts prefixed with tenant currency symbol (map + code fallback).

## Acceptance Criteria

1. Changing currency/date/timezone/time-format reflects everywhere in both portals after reload.
2. Date format dropdown shows live demo labels (e.g. "YYYY-MM-DD - 2026-08-05").
3. Invalid currency/timezone/date_format/time_format values rejected with 422.
4. Invoice PDF shows tenant currency symbol (map + code fallback).
5. Client portal follows the same formatting settings via read-only endpoint.
6. Formatting helpers efficient: Intl formatters cached, rebuilt only on settings change.

## Dependencies

- FEAT-002 (Subscription & Settings) - tenant settings keys + Settings -> Configuration UI
- FEAT-008 (Invoicing) - invoice dates/prices + PDF
- FEAT-012 (File Management & Storage) - file dates/prices
- FEAT-013 (Per-Tenant Email & Settings Tabs) - settings tabs restructure hosts the Configuration rows

## Decisions

- Efficiency via cached Intl formatters + single settings store; helpers read the store internally so call sites stay unchanged.
- Helpers API stable: `fmtPrice`, `formatDate`, `formatDateTime` are the only formatting entry points.
- Client portal gets a read-only formatting-settings endpoint (`GET /client/settings`) - same 4 formatting keys, no permission internals.
