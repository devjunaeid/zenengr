---
id: FEAT-018
title: Project Ledger (Balance-Forward) & Formal Invoice Generator
status: approved
priority: P0
source: Product decision 2026-08-07
---

# FEAT-018 - Project Ledger (Balance-Forward) & Formal Invoice Generator

## Goal

Deliver a balance-forward Project Ledger on top of the existing open-item invoicing module (NOT a replacement: formal invoices stay; the ledger becomes authoritative for what's owed), plus a formal invoice generator that produces single-project or fully custom line-item invoices with invoice_ref tagging so the ledger timeline shows what has been invoiced. The ledger stores append-only charges and manual adjustments only; the payment stream is DERIVED from existing Transactions (single source of truth, no mirror writes). The timeline merges both at read time. A per-project discount (single active, replace-on-change, audited old/new) feeds a live Summary.

## Functional Requirements

- FR-18.1: LedgerEntry model. Fields: type (`charge` | `payment` | `refund`), source_type (`project_service` | `transaction` | `manual_adjustment`), source_id, invoice_ref (nullable, set when a charge is covered by an issued invoice), entry_date, created_by, append-only and immutable (no update/delete). Indexes on (project_id, type) and (project_id, entry_date).
- FR-18.2: Payment stream derived from Transactions. No mirror writes: ledger `payment`/`refund` entries are computed at read time from the existing Transaction stream (including advances via allocations). The ledger never persists payment rows.
- FR-18.3: Project discount. Single active discount per project, type `percentage` | `fixed`, replaces on change (no stacking), audited with old/new values, NO reason note, never shown on the client timeline.
- FR-18.4: Live Summary math. Subtotal = sum of charges; Discount (percentage → round(Subtotal × v / 100, 2); fixed → min(v, Subtotal)); Total = Subtotal − Discount; Paid = sum of payments − sum of refunds (transaction stream incl. advances via allocations); Due = max(Total − Paid, 0).
- FR-18.5: Charge hooks. Attaching a ProjectService creates a `charge` LedgerEntry (amount = price at attachment, entry_date = today). Service cancelled/removed creates an offsetting adjustment entry (keeps the ledger honest).
- FR-18.6: Manual adjustment endpoint. Admin/manager only; creates a `manual_adjustment` LedgerEntry; audited.
- FR-18.7: Formal invoice generator. Single-project scope OR fully custom line items (NO multi-project). Service picker flags already-invoiced services. When generating for a discounted project, the discount is added as a negative line item so the document matches the Summary. Draft-or-issue flow reuses the existing invoice module.
- FR-18.8: invoice_ref tagging on issue. When an invoice is issued, covered ProjectService charge LedgerEntries get the invoice_ref tag → "Included in INV-…" badge on the timeline.
- FR-18.9: Client portal. Read-only project timeline (charges + payments) + Summary + issued formal invoices only.

## Acceptance Criteria

1. LedgerEntry is append-only and immutable; indexes on (project_id, type) and (project_id, entry_date); created_by recorded. (FR-18.1)
2. Attaching a service to a project creates a charge entry with amount = price at attachment and entry_date = today. (FR-18.5)
3. Cancelling/removing a service writes an offsetting adjustment entry. (FR-18.5)
4. Payments and refunds appear on the timeline from the Transaction stream (including advances via allocations); no payment rows are persisted in the ledger. (FR-18.2)
5. Discount: single active (percentage|fixed); setting a new one replaces the old; audit records old and new; no reason note; never on client timeline. (FR-18.3)
6. Summary computes live per FR-18.4: Subtotal = Σ charges; percentage discount rounds to 2dp, fixed discount caps at Subtotal; Due = max(Total − Paid, 0). (FR-18.4)
7. GET /tenant/projects/{id}/ledger and GET /client/projects/{id}/ledger (client-scoped) return {entries (merged charges + derived payments/refunds, chronological), summary}. (FR-18.4, FR-18.9)
8. Manual adjustment endpoint: admin/manager only, creates a manual_adjustment entry, audited. (FR-18.6)
9. Invoice generator: single-project or fully custom line items; picker flags already-invoiced services; discount added as negative line item on discounted projects; draft then issue. (FR-18.7)
10. On invoice issue, covered charge entries get invoice_ref and the timeline shows "Included in INV-…" badge. (FR-18.8)
11. Client portal: read-only timeline + Summary + issued invoices; no editing. (FR-18.9)
12. Cross-tenant and cross-client access is impossible. (FR-18.1, FR-18.9)

## Out of Scope

- Multi-project invoices
- billing_mode (open_item) — deferred, user decision pending
- Payment mirroring in the ledger (payment stream derived, not stored)
- Running-balance-per-row in the timeline (balance-forward summary only)

## Dependencies

- FEAT-007 (Project Management) - ProjectService attach/cancel/removal hooks
- FEAT-008 (Invoicing) - invoice model, draft/issue flow, issue_invoice change for invoice_ref tagging
- FEAT-009 (Payments & Financial Tracking) - Transaction stream (incl. advances via allocations) for derived payments
- FEAT-015 (Advances, Ledger Transactions & General Invoices) - advance allocations feed Paid

## Decisions

- Ledger is balance-forward and authoritative for what's owed; formal invoices stay (not a replacement). (Product decision 2026-08-07)
- LedgerEntry stores charges + manual adjustments only; the payment stream is derived from existing Transactions at read time (single source of truth; no mirror writes). Timeline merges both.
- Project discount: single active (percentage|fixed), replaces on change, audited old/new, NO reason note, never on client timeline.
- Summary computed live per FR-18.4; no persisted running balances.
- Invoice generator: single-project scope or fully custom line items; NO multi-project.
- On invoice ISSUE, covered ProjectService charge entries get invoice_ref → "Included in INV-…" badge.
- Service cancelled/removed → offsetting adjustment entry (keeps ledger honest).
- Client portal: read-only project timeline + Summary + issued formal invoices only.
- billing_mode (open_item) deferred (user decision pending).
- Spec superseded: the mother-invoice/auto-routing draft was never built — nothing to remove.
