---
id: FEAT-022
title: Financial Corrections, Service Price Edits & Ledger Entry Management
status: approved
priority: P0
source: User requirement 2026-09-12
---

# FEAT-022 — Financial Corrections, Service Price Edits & Ledger Entry Management

## Goal

Provide intuitive, user-friendly mechanisms for administrators and managers to correct mistakes across project services, manual ledger adjustments, direct project payments, and invoice transactions. Ensure that correcting an item immediately updates the project ledger, balance summary, live statement preview, statement PDF, and any open draft invoices without requiring destructive workarounds.

## Scope

### In Scope

- **Project Service Price Editing & Removal**:
  - Ability to edit the price of an attached service (`price_at_attachment`) directly from the Project page.
  - Automatically synchronize the project service's ledger charge entry (`LedgerEntryType.CHARGE`).
  - Automatically synchronize unissued DRAFT invoices containing this project service line item.
  - Guard against price edits if the service is already locked by an issued invoice.
  - Front-end action to remove/cancel a project service from the Services table and mobile cards with user confirmation.
- **Manual Ledger Adjustment Corrections**:
  - Ability to edit the amount, description, and date of an existing manual adjustment on the project ledger.
  - Ability to delete/remove an erroneous manual adjustment.
  - Guard against editing or deleting adjustments already locked by an issued statement invoice.
- **Payment & Transaction Corrections**:
  - **Direct Project Payments**: Ability to edit (amount, method, date, reference note) or delete direct payments recorded on the project ledger.
  - **Invoice Transactions**: Ability to delete/remove mistaken payments recorded on an invoice, with automatic recomputation of invoice balance and status (`PAID` -> `PARTIALLY_PAID` / `ISSUED`) and cleanup of unapplied advance overages.
- **Live Financial & Statement Synchronization**:
  - Immediate recalculation of project subtotal, discount, total, paid, due, and advance credit across ledger, statement preview, and PDF export.

### Out of Scope

- Modifying line items on non-draft (issued/paid) formal invoices without voiding them first (issued invoices remain tamper-proof legal documents; users must void them or adjust via ledger).
- Client portal editing capabilities (staff-only administrative correction).

## Functional Requirements

- **FR-22.1**: `PATCH /tenant/projects/{project_id}/services/{project_service_id}` allows updating `price_at_attachment`. Updates the corresponding `LedgerEntry` charge and open draft invoice line items. Returns 409 if already locked on an issued invoice.
- **FR-22.2**: UI provides "Edit Price" and "Remove Service" actions on the Project detail Services tab for staff with `manage:projects` permission.
- **FR-22.3**: `PATCH /tenant/projects/{project_id}/ledger/adjustments/{entry_id}` allows updating the amount, description, and entry date of a manual adjustment. Returns 409 if locked on an issued invoice.
- **FR-22.4**: `DELETE /tenant/projects/{project_id}/ledger/adjustments/{entry_id}` removes an erroneous manual adjustment.
- **FR-22.5**: `PATCH /tenant/projects/{project_id}/payments/{entry_id}` and `DELETE /tenant/projects/{project_id}/payments/{entry_id}` allow updating and deleting direct project payments.
- **FR-22.6**: `DELETE /tenant/invoices/{invoice_id}/transactions/{transaction_id}` removes a recorded invoice payment, cleans up any associated unapplied advance, and recalculates the invoice's net paid amount and status.
- **FR-22.7**: All correction actions emit structured audit log events (`project.service_price_updated`, `project.ledger_adjustment_updated`, `project.ledger_adjustment_deleted`, `project.payment_updated`, `project.payment_deleted`, `invoice.transaction_deleted`).
- **FR-22.8**: Project page Ledger Timeline displays interactive Edit and Delete actions on eligible manual adjustment and payment entries.

## Acceptance Criteria

1. An admin can edit the price of an attached service on a project; the service table, ledger charge, ledger summary, and live statement immediately reflect the new price.
2. An admin can remove an attached service directly from the project Services tab with confirmation.
3. An admin can edit the amount or description of a manual adjustment; the ledger timeline and summary immediately update.
4. An admin can delete a mistaken manual adjustment; the entry is removed from the ledger and balance recalculates.
5. An admin can edit or delete a direct project payment; the paid amount, due balance, and statement preview update cleanly.
6. An admin can delete a mistaken payment transaction from an invoice; invoice paid amount and status are recalculated.
7. Attempting to edit or delete items already locked by an issued invoice displays clear, actionable validation messages.
