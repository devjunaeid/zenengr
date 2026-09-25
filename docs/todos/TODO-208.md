---
id: TODO-208
story: US-069
feature: FEAT-023
title: Add Numbering System setting to Configuration page and integrate AmountInWords on inputs
status: done
priority: P1
dependencies: [TODO-207]
blocks: []
---

# TODO-208 - Add Numbering System setting to Configuration page and integrate AmountInWords on inputs

## What to do

1. Update `frontend/src/routes/app/settings/configuration/+page.svelte`:
   - Add `number_system` to SETTING_LABELS and SECTIONS (under Regional & Date / Time Formats or Currency & Accounting).
   - Render selector for `International (Millions, Billions)` and `South Asian (Lakh, Crore / Korti)`.
   - Provide live interactive example preview showing conversion for `15,000,000`.
2. Integrate `<AmountInWords value={...} />` into amount input fields across the application:
   - Line items unit price in `frontend/src/routes/app/invoices/new/+page.svelte` and `frontend/src/routes/app/invoices/[id]/edit/+page.svelte`.
   - Payment amount, refund amount, advance apply amount in `frontend/src/routes/app/invoices/[id]/+page.svelte`.
   - Record payment and advance modal amount inputs in `frontend/src/routes/app/projects/[id]/+page.svelte`.
   - Service catalog base price inputs in `frontend/src/routes/app/settings/services/new/+page.svelte` and edit page.
3. Validate layout and test interactions.

## Acceptance Check

- Changing Numbering System in Settings -> Configuration persists and updates the entire platform.
- Typing into any amount input immediately reflects in-words text beneath the label.
- No visual clutter or layout breakages on mobile or desktop.
