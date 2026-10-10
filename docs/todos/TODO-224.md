---
id: TODO-224
title: Bill-once invoice generation & explicit charges for custom invoice lines
story: US-077
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-222, TODO-223]
blocks: [TODO-226]
---

# TODO-224 - Bill-once invoicing

## Scope

- `generate_statement_invoice`: include only charges with no non-void `invoice_ref`; 422 "Nothing new to bill"; tag included charges; auto-allocate unallocated payments; stop copying transactions.
- `issue_invoice` (custom project invoice): create `LedgerEntry` CHARGE per custom line (`source_type=invoice_line`, `invoice_ref` set).
- `void_invoice`: void allocations (payment amount returns to unallocated), write reversal for invoice_line charges, clear `invoice_ref` on service/adjustment charges.
- Tests in `tests/test_statement_invoices_api.py` and `tests/test_invoices_api.py`.

## Acceptance check

AC-077.1..AC-077.3 covered; generating twice with no new charges returns 422.
