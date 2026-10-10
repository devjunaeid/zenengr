---
id: TODO-226
title: Company reports on payments & non-duplicated invoices
story: US-077
feature: FEAT-027
status: done
priority: P0
dependencies: [TODO-223, TODO-224, TODO-225]
blocks: []
---

# TODO-226 - Accurate reports

## Scope

- `services/reports.py`: collections/refunds from `payments` by `paid_on`; invoiced from issued non-void invoices; project/client breakdowns reuse ledger summary math.
- Regression test: report totals == Σ project summaries for the same filter (`tests/test_reports_api.py`).

## Acceptance check

AC-077.4, AC-077.5 pass.
