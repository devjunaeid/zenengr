---
id: FEAT-029
title: Flexible Client Billing - Contract Items, Invoice Wizard, Tax & Credit Notes
status: proposed
priority: P1
source: User requirement 2026-10-10 (financial system review, phase P2)
depends_on: FEAT-027
---

# FEAT-029 - Flexible Client Billing

## Goal

Let any business bill the way it actually works: by item and quantity, by milestone, by % progress
(running bills), by deposit, or a final invoice. Every item is billed exactly once, and corrections
go through credit notes.

## Scope

### In Scope

- **Contract (billable) items:** project services *or* free lines with qty, unit, rate, optional
  milestone link. Each item tracks billed qty/amount vs remaining.
- **Create invoice wizard** (one entry point replacing "Generate invoice" + "Custom invoice"):
  1. Select items (with partial quantity)
  2. Progress % of contract / milestone billing
  3. Deposit / advance request
  4. Final invoice: remaining items with deposits deducted automatically
- **Tax/VAT (ADR-004 Q1):** optional, off by default; tenant-named rates, default auto-applied, changeable
  per line; exclusive by default with per-invoice inclusive toggle. Invoice-level discount.
- **Retention % (ADR-004 Q4):** optional per project, withheld per invoice, released via a
  "Release retention" invoice.
- **Editable issued invoices (ADR-004):** edits keep revision history; if the new total drops below the
  amount paid, the excess becomes client advance. Voiding an issued invoice requires a reason.
- **Credit notes:** numbered, linked to the original invoice, reduce charges/billed amounts.
- **Receive payment dialog:** suggested allocation to the oldest open invoices (editable), remainder
  shown as advance.
- **Live statement** stays a read-only document (never numbered as an invoice).
- **Quote/estimate → contract items** conversion (optional, last in phase).

### Out of Scope

- Online payment gateways, multi-currency.

## Acceptance Criteria (draft)

1. "Flyer printing 100,000 pcs × 0.85" can be billed 50% as deposit and the rest as final, with the
   deposit deducted automatically.
2. A construction contract can be billed by monthly progress % with retention withheld.
3. An item can never appear on two non-void invoices beyond its quantity/amount.
4. A credit note corrects an issued invoice without voiding it, and the ledger shows the link.
