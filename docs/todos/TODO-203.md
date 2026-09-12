---
id: TODO-203
title: Backend invoice transaction deletion and status recalculation
story: US-067
feature: FEAT-022
status: done
priority: P0
---

# TODO-203 — Backend invoice transaction deletion and status recalculation

## Context

Payments recorded against invoices cannot currently be deleted if recorded erroneously.

## Requirements

1. Add `DELETE /tenant/invoices/{invoice_id}/transactions/{transaction_id}` endpoint in `backend/app/api/v1/invoices.py`.
2. In `backend/app/services/transactions.py`:
   - Implement `delete_transaction(session, tenant_id, invoice_id, transaction_id, actor_id)`:
     - Verify invoice belongs to tenant and transaction belongs to invoice.
     - Check if any `Advance` generated from this transaction was already partially/fully applied elsewhere:
       - Query `PaymentAllocation` where `advance_id` is an advance originating from this transaction. If applied, raise HTTP 422 ("Cannot delete payment: an overpayment advance generated from this transaction has already been applied.").
       - If advance exists and is untouched (`remaining_amount == amount`), delete the advance row.
     - Delete the transaction (allocations cascade-delete).
     - Recalculate remaining net paid amount on the invoice (`_invoice_net_paid`).
     - Recompute invoice status:
       - If net paid <= 0 -> `InvoiceStatus.ISSUED`.
       - If net paid < invoice.total -> `InvoiceStatus.PARTIALLY_PAID`.
       - If net paid >= invoice.total -> `InvoiceStatus.PAID`.
     - Audit log `invoice.transaction_deleted`.
3. Unit/integration tests covering transaction deletion, invoice status transition from PAID back to PARTIALLY_PAID or ISSUED, and advance cleanup.
