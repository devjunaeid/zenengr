---
id: TODO-207
story: US-069
feature: FEAT-023
title: Frontend numberToWords utility, settings store update, and AmountInWords component
status: done
priority: P1
dependencies: [TODO-206]
blocks: [TODO-208]
---

# TODO-207 - Frontend numberToWords utility, settings store update, and AmountInWords component

## What to do

1. Update `frontend/src/lib/stores/settings.svelte.js`:
   - Add `number_system: 'international'` to initial state.
   - Export getter `get number_system()`.
   - Update `setTenantSettings` to parse and store `number_system`.
2. Update `frontend/src/routes/app/+layout.js` and `frontend/src/routes/client/+layout.js` to pick and pass `number_system`.
3. Create `frontend/src/lib/utils/numberToWords.js`:
   - Implement `numberToWords(num, system)` supporting:
     - `international`: thousands, millions, billions, trillions.
     - `south_asian`: thousands, lakh, crore / korti.
     - Fractional/decimal cents handling.
     - Clean capitalization.
4. Create reusable Svelte component `frontend/src/lib/components/AmountInWords.svelte`:
   - Props: `value` (number or string), optional `currency`, optional `class`.
   - Reactively uses `tenantSettings.number_system`.
   - Renders unobtrusive, small dynamic text below labels: e.g. `(One lakh fifty thousand)` when `value > 0`.

## Acceptance Check

- Utility converts numbers to words accurately across wide ranges in both systems.
- Reactive store correctly reads tenant's configured system.
- Component renders nothing when value is empty or 0, and renders spelled-out words dynamically when value is valid.
