---
id: FEAT-030
title: Project Finance Hub - Unified Money In / Money Out / Result Experience
status: proposed
priority: P1
source: User requirement 2026-10-10 (financial system review, phase P3)
depends_on: FEAT-027, FEAT-028, FEAT-029
---

# FEAT-030 - Project Finance Hub

## Goal

Replace the separate Ledger & Financials, Invoices and Purchases tabs with one **Finance** tab that
a non-technical admin understands at a glance and can act on in seconds.

## Scope

### In Scope

- **3 primary actions:** `+ Add cost`, `Receive payment`, `Create invoice ▾`; secondary actions
  (discount, adjustment, credit note, statement, lock) under `⋯ More`.
- **KPI cards (plain language):** Contract, Invoiced, Received, Client owes, Advance | Total cost,
  Paid out, We owe, **Profit (margin %)**. Every number drills down to the entries behind it.
- **Sub-tabs:** Overview | Billing (items · invoices · payments) | Costs | Journal | Statement.
- **Journal:** single chronological timeline of all money events with filter chips, running balance,
  source links, void/reversal links and audit info.
- **Overview insights:** cost by category, cash in vs cash out over time, warnings (overdue invoices,
  unpaid vendors, over-budget categories once FEAT-031 lands).
- **Mobile quick-add cost** (photo receipt + amount + category).
- **Code health:** split `routes/app/projects/[id]/+page.svelte` (5,000+ lines) finance parts into
  focused components under `lib/components/finance/`.
- Consistent colour language: green = received/good, red = client overdue, amber = we owe.

### Out of Scope

- Company-level dashboards (FEAT-031 / existing FEAT-025 Reports).

## Acceptance Criteria (draft)

1. A first-time non-technical user can record a cost, receive a payment and create an invoice without
   guidance (validated in a hallway test).
2. All project money figures are visible on one screen without switching tabs.
3. Finance tab first paint ≤ 1s on desktop with lazy-loaded sub-tabs (FEAT-024 pattern).
