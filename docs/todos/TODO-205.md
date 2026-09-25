---
id: TODO-205
story: US-068
feature: FEAT-023
title: Add Due Date column to main invoices list table and mobile cards
status: done
priority: P1
dependencies: []
blocks: []
---

# TODO-205 - Add Due Date column to main invoices list table and mobile cards

## What to do

1. Edit `frontend/src/routes/app/invoices/+page.svelte`:
   - In desktop table (`lg:block`), add `Due Date` column in `<thead>` and `<tbody>`.
   - Format `inv.due_date` using `formatDate(inv.due_date)` with fallback `—`.
   - If `inv.due_date` is in the past and `inv.status` is not `'paid'` or `'void'`, display an overdue visual badge or warning tone.
   - In mobile cards (`lg:hidden`), add `Due:` alongside `Issued:` date in the metadata grid.

## Acceptance Check

- Desktop invoice table displays `Due Date` column with formatted date values.
- Mobile cards display `Due:` date.
- Overdue unpaid invoices display subtle visual highlighting.
