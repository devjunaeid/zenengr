---
id: FEAT-027
title: Financial Accuracy - Single Payment Source, Non-Duplicating Invoicing & Auditable Corrections
status: proposed
priority: P0
source: User requirement 2026-10-10 (financial system review, phase P0)
---

# FEAT-027 - Financial Accuracy Foundation

## Goal

Make every project/company money figure (billed, received, due, advance, report KPIs) exact and
traceable, so later phases (costs & profit, flexible billing, finance hub) are built on numbers
the company can trust.

## Problems addressed (found in 2026-10-10 review)

1. Client payments are stored in two places (`LedgerEntry` type PAYMENT for direct payments and
   `Transaction` for invoice payments) and merged at read time by an amount+date+direction
   heuristic (`services/ledger.py` `compute_project_ledger_summary`, `get_project_ledger`). Two
   genuine same-amount same-day payments collapse into one; any note containing "synced" is ignored.
2. `generate_statement_invoice` re-bills **all** services and adjustments on every run and **copies**
   prior transactions onto the new invoice.
3. Company reports sum `Invoice.total` and `Transaction` rows, so repeated statement invoices inflate
   "Invoiced" and "Collected"; direct project payments with no invoice are missing from "Collected".
4. Custom invoice lines are added to the project subtotal by a side query instead of being explicit
   ledger charges.
5. Two unreconciled advance concepts (project `paid - total` vs client `Advance` table).
6. Ledger adjustments/payments can be hard-deleted; purchase entries have no audit trail.

## Scope

### In Scope

- **Single payment source of truth:** new `payments` table (one row per money receipt or refund from a
  client). Invoice-level `transactions` become *allocations* of a payment (`transactions.payment_id`
  FK, required for new rows). Direct project payments = payments with no/partial allocation.
- **Unallocated balance = advance:** project/client advance is computed from unallocated payment
  amounts. `Advance` table retired (migrated to payments); `apply_advance` becomes "allocate
  unallocated payment to invoice".
- **Bill-once rule:** a ledger charge can be included on at most one non-void invoice. "Generate
  invoice" bills only unbilled charges and auto-allocates unallocated payments (oldest first) instead
  of copying transactions.
- **Explicit charges:** issuing a custom project invoice writes explicit `LedgerEntry` CHARGE rows
  (`source_type = invoice_line`); voiding writes reversal rows. Summary = sum of ledger charges only.
- **Accurate reports:** collections = sum of payments (receipts − refunds) by `paid_on`; invoiced =
  issued non-void invoices with no double counting.
- **Flexible, auditable corrections (ADR-004 "fix anything, lose nothing"):** payments, adjustments
  and allocations are fully editable; every edit stores before/after history. Delete = soft delete
  (void) with optional reason, excluded from totals, **restorable** by admin; Undo toast after actions.
  Purchase entries create/update/delete are audited.
- **Data migration with dry-run report:** backfill payments from existing ledger PAYMENT rows,
  transactions and advances; detect "synced" duplicate transactions and overlapping statement
  invoices; produce a reconciliation report for admin review before committing.

### Out of Scope

- Costs/profit, vendors, categories (FEAT-028).
- Tax, credit notes, invoice wizard, quantity/unit billing (FEAT-029).
- New Finance hub UI (FEAT-030). UI changes here are limited to what the data model needs.

## Functional Requirements

- **FR-27.1:** `Payment` fields: `id, tenant_id, client_id, project_id (nullable for general), kind
  (receipt|refund), amount > 0, method, paid_on (date), reference, notes, recorded_by_id, created_at,
  voided_at, voided_by_id, void_reason`.
- **FR-27.2:** Sum of active allocations of a payment ≤ payment amount (enforced in service + DB check
  via trigger or locked recompute). Unallocated = amount − allocated.
- **FR-27.3:** Project summary: `paid = Σ active receipts − Σ active refunds`; `total = Σ charges − discount`;
  `due = max(total − paid, 0)`; `advance = max(paid − total, 0)`. No heuristic dedup anywhere.
- **FR-27.4:** Invoice `paid` = Σ active allocations to it; status recomputed on every allocation change.
- **FR-27.5:** `POST /tenant/projects/{id}/payments` records a payment and optionally allocates it
  (`allocations: [{invoice_id, amount}]` or `auto_allocate: true`). Recording a payment on an invoice
  page creates a Payment + allocation in one call (existing endpoint keeps its contract).
- **FR-27.6:** `PATCH /tenant/payments/{id}` may change amount, date, method, reference, notes and
  allocations (amount cannot drop below allocated total without re-allocating; the UI offers to
  release allocations). `POST /tenant/payments/{id}/void` (optional reason) and
  `POST /tenant/payments/{id}/restore`. Paying more than due shows a warning, not an error.
- **FR-27.7:** Generate invoice includes only charges with no non-void `invoice_ref`; returns 422
  "Nothing new to bill" when empty. Voiding an invoice clears `invoice_ref` on its charges.
- **FR-27.8:** Reports (`services/reports.py`) use payments for collections and exclude void invoices;
  results match the sum of project summaries for the same filter.
- **FR-27.9:** Ledger adjustment delete becomes soft delete (restorable); audit events record old/new
  values; `GET /tenant/audit/{entity_type}/{id}` returns record history for the History panel.
- **FR-27.10:** Purchase entry create/update/delete emit `purchase.created|updated|deleted` audits.
- **FR-27.11:** Migration offers `--dry-run` producing a per-project reconciliation (old vs new paid/due,
  duplicates found, overlapping statements) before `--commit`. Original rows are retained.

## Acceptance Criteria

1. Two payments of the same amount on the same day both count toward Paid.
2. Generating an invoice twice without new charges does not create a second invoice with the same items.
3. Company report "Collected" equals the sum of all project Paid values for the same date range,
   including direct payments with no invoice.
4. Overpaying an invoice leaves the remainder as unallocated payment visible as Advance, and it can be
   allocated to another invoice.
5. Voided payments/adjustments remain visible (with optional reason, actor and time), are excluded
   from totals, and can be restored in one click.
6. Every financial create/update/void (including purchases) appears in the audit log with before/after.
7. Dry-run migration report lists every project whose figures change and why.
