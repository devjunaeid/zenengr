---
id: TODO-193
title: Automated tests & end-to-end verification for statement invoices
feature: FEAT-019
story: US-064
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-187, TODO-188, TODO-189, TODO-190, TODO-191, TODO-192]
blocks: []
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-193 — Automated tests & end-to-end verification for statement invoices

## Description

- Add pytest test suite in `backend/tests/test_statement_invoices_api.py` testing:
  - Statement live preview calculation (charges, payments, advances, overpayment credit, due).
  - Statement PDF generation.
  - Generate statement invoice flow (tagging, line items, sequential numbering).
  - Subsequent multi-day invoice generation (Day 1 snapshot, Day 3 incremental entries + new due/advance).
  - Client portal authorization and access isolation.
- Run frontend type check, lint, and build verification.

## Acceptance criteria

- [ ] All new tests pass (`uv run pytest tests/test_statement_invoices_api.py`).
- [ ] Frontend check (`npm run check`) and lint (`npm run lint`) pass.
