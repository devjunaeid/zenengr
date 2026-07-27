---
id: FEAT-009
title: Payments & Financial Tracking
status: approved
priority: P0
source: docs/prd.md §6.9
---

# FEAT-009 — Payments & Financial Tracking

## Goal

Let tenant staff record manual payments against invoices, including partial payments with line-item allocation. Invoice status auto-updates based on payment amounts. Project-level financial rollups aggregate across all invoices. All financial records are immutable once finalized.

## Scope

### In Scope
- Manual transaction recording: amount, date, method (bank transfer, card, cash, other), reference note, recorded-by user
- Partial payments with auto-update of invoice status (Partially Paid → Paid)
- Payment allocation across line items: system proposes proportional/FIFO, tenant staff can override
- Project financial rollups: Total Invoiced, Total Paid, Total Outstanding (computed, not stored)
- Client Portal view of payment history and outstanding balance (read-only)
- Immutability of finalized financial records (corrections via new records)

### Out of Scope
- Payment gateway integration / online collection (Phase 2, behind `client_portal_payments` flag)
- Payment gateway auto-reconciliation / webhooks (Phase 2, per §3.2)
- Automated recurring billing to clients (Phase 2, per §3.2)
- Credit notes / refunds as distinct record type (Phase 2 candidate)

## Functional Requirements

- FR-9.1: Tenant Admin/Manager can record a Transaction (payment) against an Invoice: amount, date, method (bank transfer, card, cash, other), reference note, recorded-by user.
- FR-9.2: A Transaction can be a **partial payment**. Invoice status must auto-update to `Partially Paid` when `0 < amount paid < total`, and `Paid` when fully covered.
- FR-9.3: Where an Invoice contains multiple line items, the system supports **allocating a payment across specific line items** ("how much has been paid toward Service X"). Default: system proposes proportional/FIFO auto-allocation; tenant staff can manually override.
- FR-9.4: Project-level financial summary aggregates across all invoices/transactions: Total Invoiced, Total Paid, Total Outstanding — optionally per Service.
- FR-9.5: Client Users can view payment history and outstanding balance in the Client Portal (view-only in MVP).
- FR-9.6: All financial records (invoices, transactions) are immutable once finalized — corrections via new records, never destructive edits.

## Acceptance Criteria

1. Tenant Admin/Manager can record a full payment against an Issued invoice; invoice status changes to Paid.
2. Recording a partial payment (amount < total) sets invoice status to Partially Paid.
3. Multiple partial payments accumulate; invoice becomes Paid when sum >= total.
4. Payment allocation across line items: system proposes proportional allocation; tenant staff can manually adjust per line item.
5. Project financial summary shows correct totals: sum of all invoice totals, sum of all payments, balance due.
6. Client Portal shows payment history and outstanding balance (read-only).
7. Once recorded, a transaction cannot be edited or deleted only (if needed) offset by a corrective transaction.
8. Financial rollups are computed from live data; updating a payment immediately changes project totals.

## Dependencies

- FEAT-008 (Invoicing) — payments are linked to invoices
- FEAT-007 (Project Management) — financial rollups are per-project
- FEAT-005 (Client Management) — client-level outstanding balance rollups

## Decisions

- **Manual payment recording only in MVP** (no gateway).
- **Partial payments auto-update invoice status.**
- **Line-item allocation:** system proposes proportional/FIFO auto-allocation by default; tenant staff can manually override per line item.
- **Financial records append-only** — immutable once finalized.
