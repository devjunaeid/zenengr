---
id: TODO-090
title: Invoice status auto-update logic
feature: FEAT-009
story: US-035
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-089]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-090 — Invoice status auto-update logic

## Description

Implement logic: on payment recording, recalculate invoice paid amount and update status. Full payment -> Paid. Partial -> Partially Paid. Multiple partial payments accumulate.

## Acceptance criteria

- [x] After recording transaction: sum payments for invoice.
- [x] If sum >= total: set status=Paid (FR-9.2).
- [x] If sum > 0 and < total: set status=PartiallyPaid (FR-9.2).
- [x] Multiple partial payments accumulate toward total (FR-9.2 AC-3).
- [x] Status update happens in same transaction as payment recording.

## Notes

Status recompute in same transaction as recording: sum(transactions) >= total -> paid; > 0 -> partially_paid; multiple partials accumulate. Overpayment allowed (status paid).

