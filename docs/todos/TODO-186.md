---
id: TODO-186
title: Tests + verification + docs sync
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-178, TODO-179, TODO-180, TODO-181, TODO-182, TODO-183, TODO-184, TODO-185]
blocks: []
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-186 - Tests + verification + docs sync

## Description

End-to-end tests: LedgerEntry model + append-only enforcement + indexes, Project discount fields, charge hook on service attach, offsetting adjustment on cancel/removal, manual adjustment endpoint (admin/manager + audit), discount editor API (replace, clear, audit old/new), ledger API both realms + cross-tenant guard, summary math (percentage rounding, fixed cap, advances via allocations in Paid, Due floor at 0), invoice generator (single-project/custom, already-invoiced flags, discount line item, draft/issue), invoice_ref tagging on issue + badge data, client portal read-only. Full suite green. Sync docs (stories/todos status, progress).

## Acceptance criteria

- [x] Tests: model + append-only + indexes. (FR-18.1)
- [x] Tests: charge hook + reversal + manual adjustment. (FR-18.5, FR-18.6)
- [x] Tests: discount API (replace, clear, audit old/new). (FR-18.3)
- [x] Tests: ledger API staff + client scope + cross-tenant guard. (FR-18.9)
- [x] Tests: summary math incl. percentage rounding, fixed cap, advances in Paid, Due floor. (FR-18.4)
- [x] Tests: invoice generator + invoice_ref tagging + badges. (FR-18.7, FR-18.8)
- [x] Full suite green; docs synced.

## Notes

- Shipped: 688 backend tests green; frontend check/lint/build clean; live-verified.
