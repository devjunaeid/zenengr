---
id: TODO-198
story: US-066
feature: FEAT-021
status: done
priority: P1
assignee: ""
created: "2026-09-09"
updated: "2026-09-09"
---

# TODO-198 — Backend schemas, services, API endpoints, and PDF generation with `billed_to`, `invoice_type`, and date range filters

## Context

Expose `billed_to` in invoice create/update schemas and API endpoints. Support filtering invoices by `invoice_type` (`all`, `project`, `general`), `date_from`, and `date_to`. In PDF generation, render the `billed_to` details for general invoices.

## Acceptance criteria

- [x] Pydantic schemas updated: `InvoiceCreateRequest`, `InvoiceUpdateRequest`, `InvoiceResponse`, `InvoiceListItem` include `billed_to`.
- [x] `InvoiceListItem` includes `is_general`.
- [x] Service `create_draft_invoice` and `update_draft_invoice` persist and audit `billed_to`.
- [x] Service `list_invoices` filters by `invoice_type` (`project` vs `general`) and date range (`date_from`, `date_to`).
- [x] Endpoint `GET /tenant/invoices` accepts `invoice_type`, `date_from`, `date_to` queries.
- [x] `render_invoice_pdf` in `backend/app/services/pdf.py` renders `billed_to` data in the "BILLED TO" header when available.
- [x] Automated tests in `backend/tests/test_invoices_api.py` verify creation, update, filtering, and PDF rendering.
