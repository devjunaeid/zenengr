---
id: FEAT-019
title: Cumulative Statement Invoicing & Realtime Financial Sync
status: approved
priority: P0
source: User requirement 2026-08-26
---

# FEAT-019 — Cumulative Statement Invoicing & Realtime Financial Sync

## Goal

Provide a real-time running financial statement for projects that synchronizes service additions/updates and payments/advances chronologically. Enable tenant administrators to preview and print the live project statement at any point, and issue cumulative snapshot invoices (with sequential numbering) that capture the progressive history (services, payments, net due, or advance credits) accessible to both staff and client portals.

## Functional Requirements

- **FR-19.1: Live Chronological Financial Stream.** Projects maintain a chronological stream of charges (services/quantities/amounts with dates) and payments/advances (dates, methods/references, amounts).
- **FR-19.2: Realtime Advance & Due Calculation:**
  - $\text{Total Charges} = \sum \text{Services / Adjustments}$
  - $\text{Total Paid} = \sum \text{Payments} + \text{Applied Advances}$
  - When $\text{Total Charges} \ge \text{Total Paid}$: $\text{Net Due} = \text{Total Charges} - \text{Total Paid}$, $\text{Advance Balance} = 0$.
  - When $\text{Total Paid} > \text{Total Charges}$: $\text{Net Due} = 0$, $\text{Advance Balance} = \text{Total Paid} - \text{Total Charges}$ (client overpayment/credit).
- **FR-19.3: Live Statement Preview & On-Demand Print.** Tenant Admin can view and print/export the current live financial statement PDF at any time without issuing an invoice.
- **FR-19.4: Cumulative Snapshot Invoice Generation.** Tenant Admin can click "Generate Statement Invoice" to freeze the current progressive state into an official issued invoice (`INV-XXXX`).
- **FR-19.5: Statement-Style Invoice PDF & View.** The invoice document formats line items chronologically:
  - Charges: `Date | Service Description | Qty | Unit Price | Amount`
  - Payments: `Date | Payment Received (via Method / Ref) | — | — | -Amount`
  - Totals: `Total Charges`, `Total Paid / Credits`, `Balance Due`, and `Advance Credit` (if overpaid).
- **FR-19.6: Dual-Portal Access.** Issued statement invoices are immediately accessible and downloadable by both Tenant Admin and Client Portal users.

## Acceptance Criteria

1. Adding/updating services and recording payments immediately updates the project's live financial stream and due/advance amounts. (FR-19.1, FR-19.2)
2. If payments exceed charges, the system calculates and displays the positive advance/credit balance while setting due to $0. (FR-19.2)
3. Tenant Admin can preview and print the live project financial statement at any time. (FR-19.3)
4. Generating an invoice from the live statement issues a formal invoice with gapless sequential number (`INV-XXXX`) containing the chronological charges and payments. (FR-19.4, FR-19.5)
5. Subsequent statement invoices on later dates reflect the cumulative progressive ledger (previous entries + new services/payments + updated due/advance). (FR-19.4, FR-19.5)
6. Invoice PDF displays clean chronological rows for services and payments with due amount and advance credit calculations. (FR-19.5)
7. Both Tenant Admin and Client users can view and download the issued statement invoices. (FR-19.6)

## Dependencies

- FEAT-007 (Project Management)
- FEAT-008 (Invoicing)
- FEAT-009 (Payments & Financial Tracking)
- FEAT-015 (Advances & Ledger Transactions)
- FEAT-018 (Project Ledger & Invoice Tagging)
