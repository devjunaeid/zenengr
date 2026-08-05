---
id: FEAT-015
title: Advances, Ledger Transactions & General Invoices
status: approved
priority: P0
source: Product decision 2026-08-05
---

# FEAT-015 - Advances, Ledger Transactions & General Invoices

## Goal

Overpayments become client advances (extra/advance payments) manually applicable to invoices; transactions become debit/credit ledger entries incl. refunds; general (non-project, non-client) invoices for tenant-internal billing.

## Functional Requirements

- FR-15.1: General invoices: `Invoice.project_id` and `client_id` become nullable; general invoices have NEITHER (tenant-internal invoicing: internal works/misc charges); custom line items only; staff-only visibility (never in client portal, never in client financial rollups); same gapless numbering sequence; drafts/issue/void behave like project invoices.
- FR-15.2: Transaction direction: Transaction gains direction enum DEBIT (money in / receipt) and CREDIT (money out / refund); refund endpoint creates a credit entry (reversing an applied payment or reducing advance); amounts immutable after recording.
- FR-15.3: Advance from overpayment: recording a payment larger than the invoice's remaining balance splits it - applied portion covers the invoice, excess becomes an ADVANCE (client-scoped for client/project invoices; unassigned for general invoices).
- FR-15.4: Manual advance application: `POST /tenant/invoices/{id}/apply-advance {amount?}` moves client advance (or unassigned advance for general invoices) onto the invoice as a payment/allocation; invoice status recomputes (partially_paid/paid); audited.
- FR-15.5: Advance balance: client advance balance = advances - applied - refunded, computed live from ledger; exposed on client detail (staff) and client portal.
- FR-15.6: Ledger: staff client detail shows a Ledger of debit/credit entries with running balance; client portal shows their payment history as ledger rows with balance; invoice status auto-update accounts for advances.
- FR-15.7: General invoices excluded from project + client financial rollups and client portal lists by construction (no project/client linkage).

## Acceptance Criteria

1. General invoice create/issue/void are staff-only and never client-visible.
2. Overpay creates an advance.
3. apply-advance moves credit onto invoice and updates status.
4. Refund recorded as credit entry and audited.
5. Ledger shows Dr/Cr entries with running balance.
6. Rollups exclude general invoices.

## Out of Scope (Phase 2)

- Multi-currency
- Automatic advance application
- Credit notes
- Journal entries

## Dependencies

- FEAT-008 (Invoicing) - invoice lifecycle, line items, gapless numbering, drafts/issue/void
- FEAT-009 (Payments & Financial Tracking) - transactions, allocations, invoice status auto-update

## Decisions

- Manual apply of advances (per user).
- Refunds in scope (per user).
- General invoices have no project/client (per user).
- Advance from overpay split (per user).
