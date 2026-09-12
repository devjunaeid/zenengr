---
id: TODO-204
title: Frontend financial corrections UI for services, ledger entries, and transactions
story: US-067
feature: FEAT-022
status: done
priority: P0
---

# TODO-204 — Frontend financial corrections UI for services, ledger entries, and transactions

## Context

Staff need an intuitive and accessible UI to correct service prices, remove mistakenly attached services, edit/delete manual adjustments and project payments, and remove mistaken invoice payments.

## Requirements

1. **Client API Functions**:
   - In `frontend/src/lib/api/projects.js`:
     - `updateProjectServicePrice(fetchFn, token, projectId, projectServiceId, price)`
     - `removeProjectService(fetchFn, token, projectId, projectServiceId)`
     - `updateLedgerAdjustment(fetchFn, token, projectId, entryId, data)`
     - `deleteLedgerAdjustment(fetchFn, token, projectId, entryId)`
     - `updateProjectPayment(fetchFn, token, projectId, entryId, data)`
     - `deleteProjectPayment(fetchFn, token, projectId, entryId)`
   - In `frontend/src/lib/api/invoices.js`:
     - `deleteTransaction(fetchFn, token, invoiceId, transactionId)`
2. **Project Details Services Tab**:
   - Add Actions column to desktop table and mobile cards.
   - "Edit Price" dialog: displays service name, current price, input for new price, and visual feedback that ledger/statements will update.
   - "Remove Service" confirmation modal: warns if milestones or draft items will be affected, calls API, and updates project state.
3. **Project Details Ledger Tab**:
   - For `manual_adjustment` entries: add "Edit" and "Delete" buttons/menu.
     - Edit dialog: loads existing amount and description, updates live.
     - Delete confirmation dialog.
   - For direct `payment` entries: add "Edit" and "Delete" buttons/menu.
     - Edit dialog: loads amount, method, date, reference note.
     - Delete confirmation dialog.
   - Immediately refresh ledger entries, summary rollups, and statement preview after mutation.
4. **Invoice Details Page (`/app/invoices/[id]`)**:
   - Add "Delete Payment" button in Transactions table with confirmation modal.
   - Updates invoice status badge, paid amount, and balance due immediately.
