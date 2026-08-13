---
id: TODO-173
title: Hook event producers
feature: FEAT-017
story: US-059
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-170]
blocks: [TODO-174, TODO-177]
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-173 - Hook event producers

## Description

Emit notifications from existing business flows: comment created (shared only; staff with view/comments + client mirror), invoice issued (staff view/invoices + client), payment recorded (staff view/payments or invoices + client), refund recorded, advance applied (staff), milestone completed (staff view/milestones + client), project created (staff view/projects). Tests per hook.

## Acceptance criteria

- [x] Comment created (shared only; staff with view/comments permission + client mirror). (FR-17.3, AC-3/4)
- [x] Invoice issued (staff view/invoices + client). (FR-17.3)
- [x] Payment recorded (staff view/payments or invoices + client). (FR-17.3)
- [x] Refund recorded; advance applied (staff). (FR-17.3)
- [x] Milestone completed (staff view/milestones + client). (FR-17.3)
- [x] Project created (staff view/projects). (FR-17.3)
- [x] Tests per hook: staff permission scoping + client mirror + pref filtering.

## Notes

- Internal-only comments never notify (shared only).
- Reuses recipient resolution helpers from TODO-170.
- Shipped: event hooks wired (comment shared, invoice issued, payment, refund, advance applied, milestone, project created) - never break actions; per-hook tests.
