---
id: FEAT-031
title: Budgets, Financial Controls & Company Insights
status: proposed
priority: P2
source: User requirement 2026-10-10 (financial system review, phase P4)
depends_on: FEAT-028, FEAT-029
---

# FEAT-031 - Budgets, Financial Controls & Company Insights

## Goal

Give management control over project money: plan vs actual, early warnings, locked periods, and
company-wide receivables/payables/profit views.

## Scope

### In Scope

- **Project budgets (ADR-004 Q3):** per cost category by default, optional line-level (BOQ) breakdown
  when a category is expanded; budget vs actual with % used and over-budget warnings.
- **Period lock (main integrity control per ADR-004):** "Books locked up to <date>" blocks creating/editing/voiding financial records dated
  on or before the lock (admin can unlock, audited).
- **Reports extensions (FEAT-025):** Profit/Loss by project, client and category; receivables aging
  (0-30 / 31-60 / 61-90 / 90+); vendor payables; cash in vs out.
- **Vendors page:** purchased, paid, owed per vendor with drill-down.
- **Industry templates** at tenant setup (Construction, Printing, Agency, General) seeding cost
  categories, units and sample budget structure.
- **CSV import/export** for costs, payments and invoices.

### Out of Scope

- Full double-entry general ledger / chart of accounts, bank reconciliation, payroll.

## Acceptance Criteria (draft)

1. A project with a material budget of 2,000,000 and spend of 2,160,000 shows "Material 108% - over by
   160,000" on its Finance overview.
2. Records dated inside a locked period cannot be changed without an audited unlock.
3. Aging report totals equal the sum of client outstanding balances.
