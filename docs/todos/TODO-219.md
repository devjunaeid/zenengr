---
id: TODO-219
title: Mobile Sticky Action Bars and Touch Target Hardening
story: US-075
feature: FEAT-026
status: completed
priority: P1
dependencies: []
blocks: []
---

# TODO-219 - Mobile Sticky Action Bars and Touch Target Hardening

## Context

On long mobile forms (such as `/app/clients/new`, `/app/invoices/new`, `/app/projects/new`), users must scroll to the very bottom to submit or cancel. Furthermore, small tap targets (< 44px) frustrate mobile users.

## Scope

- Implement sticky bottom mobile action bar pattern (`sticky bottom-0 bg-white/95 backdrop-blur-sm border-t p-3 safe-bottom sm:static`) across form views.
- Ensure all clickable buttons, tab buttons, combobox triggers, and pagination icons meet the 44×44px minimum tap target requirement on mobile devices.
- Add input attributes (`inputmode="numeric"`, `enterkeyhint="next"|"done"`, `autocomplete`) across financial and contact fields.

## Acceptance check

On mobile viewports (390px width), action buttons remain accessible at the bottom of the screen during form entry, and all interactive controls can be tapped comfortably with thumbs.
