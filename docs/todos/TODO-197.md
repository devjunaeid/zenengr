---
id: TODO-197
story: US-066
feature: FEAT-021
status: done
priority: P1
assignee: ""
created: "2026-09-09"
updated: "2026-09-09"
---

# TODO-197 — Database model and migration for `invoices.billed_to` JSONB column

## Context

General invoices currently have `project_id = NULL` and no direct client association. To support recipient and billing information on General Invoices, add a `billed_to` JSONB column to the `invoices` table.

## Acceptance criteria

- [x] Add `billed_to` column to `Invoice` model in `backend/app/models/invoice.py` (`JSONB`, `default=dict`, `nullable=True`).
- [x] Create Alembic migration script adding `billed_to` to `invoices` table with server default `'{}'`.
- [x] Run migration and verify clean upgrade on Postgres database.
