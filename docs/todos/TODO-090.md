---
id: TODO-090
title: Invoice status auto-update logic
feature: FEAT-009
story: US-035
status: proposed
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

- [ ] After recording transaction: sum payments for invoice.
- [ ] If sum >= total: set status=Paid (FR-9.2).
- [ ] If sum > 0 and < total: set status=PartiallyPaid (FR-9.2).
- [ ] Multiple partial payments accumulate toward total (FR-9.2 AC-3).
- [ ] Status update happens in same transaction as payment recording.

## Notes

