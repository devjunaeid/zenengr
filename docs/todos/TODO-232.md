---
id: TODO-232
title: Verification of dynamic price updates with existing payments & frontend reconciliation
story: US-079
feature: FEAT-029
status: done
priority: P0
dependencies: [TODO-230, TODO-231]
blocks: []
---

# TODO-232 - Verification of dynamic price updates with existing payments & frontend reconciliation

## Scope

- Test scenario 1: Project with attached service ($1,000) and direct payment ($500). Update service price to $1,500. Verify total=$1,500, paid=$500, due=$1,000.
- Test scenario 2: Project with attached service ($1,000), issued invoice ($1,000), and transaction payment ($600). Update service price to $1,800. Verify update succeeds, total=$1,800, paid=$600, due=$1,200.
- Test scenario 3: Project with multiple services, price reduction below paid amount (e.g. price $1,000 -> $800 after paying $1,000). Verify total=$800, paid=$1,000, due=$0, advance_balance=$200.
- Verify frontend refreshFinancials properly renders updated numbers.

## Acceptance check

- All US-079 acceptance criteria verified with targeted pytest tests.
