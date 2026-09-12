---
id: TODO-202
title: Backend manual adjustment & project payment update/delete endpoints
story: US-067
feature: FEAT-022
status: done
priority: P0
---

# TODO-202 — Backend manual adjustment & project payment update/delete endpoints

## Context

Admins can enter mistaken manual adjustments or direct project payments on the ledger, but currently have no way to modify or remove them.

## Requirements

1. **Manual Adjustments**:
   - `PATCH /tenant/projects/{project_id}/ledger/adjustments/{entry_id}`:
     - Request schema `AdjustmentUpdateRequest`: `amount: Decimal | None`, `description: str | None`, `entry_date: date | None`.
     - Validates `entry.source_type == MANUAL_ADJUSTMENT`.
     - Checks `invoice_ref is None` (returns 409 if already locked on an issued invoice).
     - Updates fields and audits `project.ledger_adjustment_updated`.
   - `DELETE /tenant/projects/{project_id}/ledger/adjustments/{entry_id}`:
     - Validates `entry.source_type == MANUAL_ADJUSTMENT` and `invoice_ref is None`.
     - Deletes the ledger entry and audits `project.ledger_adjustment_deleted`.
2. **Direct Project Payments**:
   - `PATCH /tenant/projects/{project_id}/payments/{entry_id}`:
     - Request schema `ProjectPaymentUpdateRequest`: `amount: Decimal | None`, `method: PaymentMethod | None`, `entry_date: date | None`, `reference_note: str | None`.
     - Validates `entry.type == PAYMENT` and `entry.source_id is None`.
     - Checks lock state if `invoice_ref` set.
     - Updates amount, formatted description, date, and audits `project.payment_updated`.
   - `DELETE /tenant/projects/{project_id}/payments/{entry_id}`:
     - Validates `entry.type == PAYMENT` and `entry.source_id is None`.
     - Deletes the ledger entry and audits `project.payment_deleted`.
3. Unit/integration tests covering editing and deleting adjustments and project payments.
