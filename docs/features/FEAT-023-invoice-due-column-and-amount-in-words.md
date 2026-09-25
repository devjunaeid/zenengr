---
id: FEAT-023
title: Invoice Table Due Column & Dynamic Amount in Words with Regional Numbering Systems
status: approved
priority: P1
source: User requirement 2026-09-25
---

# FEAT-023 - Invoice Table Due Column & Dynamic Amount in Words with Regional Numbering Systems

## Goal

1. Display the invoice Due date column on the main invoices table (`/app/invoices`) for both desktop and mobile card views.
2. Introduce tenant-configurable numbering system settings (`international` vs `south_asian` / Lakh-Crore) in Tenant Configuration.
3. Provide live, reactive "amount in words" support displayed beneath input labels on amount/price input fields throughout the platform.

## Scope

### In Scope

- **Main Invoice Table Due Column:**
  - Add `Due Date` column in the desktop invoice table (`/app/invoices`).
  - Add Due date display in mobile invoice cards alongside Issue date.
  - Highlight overdue dates when the due date has passed and the invoice is neither paid nor void.
- **Tenant Numbering System Configuration:**
  - Add `number_system` setting in tenant settings (backend `DEFAULT_SETTINGS` and validation: `international` and `south_asian`).
  - Include `number_system` in client formatting keys for portal parity.
  - Update `frontend/src/lib/stores/settings.svelte.js` to reactively track `number_system`.
  - Add `Numbering System` dropdown to `Settings -> Configuration` under Regional & Date / Time with live preview ("15,000,000 -> Fifteen million" vs "One crore fifty lakh").
- **Dynamic Amount in Words Utility & UI:**
  - Create `frontend/src/lib/utils/numberToWords.js` supporting standard International (Thousands, Millions, Billions) and South Asian (Thousands, Lakhs, Crores / Korti), including decimal handling.
  - Create `<AmountInWords value={...} />` component (or small dynamic label text) showing words reactively beneath input labels.
  - Integrate across amount inputs:
    - Invoice create & edit unit prices (`/app/invoices/new`, `/app/invoices/[id]/edit`)
    - Invoice payment, refund, and advance allocation dialogs (`/app/invoices/[id]`)
    - Project payments, advances, and service price overrides (`/app/projects/[id]`, `/app/projects/new`)
    - Service catalog base prices (`/app/settings/services/new`, `/app/settings/services/[id]/edit`)

### Out of Scope

- Multi-language translation of numbers into Bengali script or Hindi script (English words with Lakh/Crore vs Million/Billion).
- Modifying legal PDF documents' static number formats unless configured.

## Functional Requirements

- **FR-23.1:** `/app/invoices` table displays a `Due Date` column formatted per tenant date format, with subtle overdue indicator if overdue and unpaid.
- **FR-23.2:** Backend supports `number_system` tenant setting with values `international` (default) and `south_asian` (with `indian` alias).
- **FR-23.3:** Settings -> Configuration allows admins to switch between `International (Millions, Billions)` and `South Asian (Lakh, Crore / Korti)`.
- **FR-23.4:** Amount input fields reactively display the number converted to words directly below the input label as the user types.

## Acceptance Criteria

1. Navigating to `/app/invoices` shows Due Date in the table header and rows, and inside mobile cards.
2. Tenant settings configuration allows selecting International vs South Asian numbering system with instant persistence.
3. Typing in any amount input immediately updates the dynamic words preview beneath the label in the configured number system.
4. When input is empty, null, or 0, the words preview remains clean and hidden.
5. All backend and frontend lint and tests pass.
