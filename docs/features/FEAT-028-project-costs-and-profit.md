---
id: FEAT-028
title: Project Costs (Money Out), Vendors & Profit/Loss
status: proposed
priority: P1
source: User requirement 2026-10-10 (financial system review, phase P1)
depends_on: FEAT-027
---

# FEAT-028 - Project Costs, Vendors & Profit/Loss

## Goal

Replace the isolated "Purchases" tab with a **Costs** module that captures everything spent on a
project (material, labour, sub-contractor, transport, design, overhead…), who it was bought from,
whether it is paid, and rolls up into a live **Profit / Margin** for each project. Must work for any
business (civil construction, printing, agency) and be usable by non-technical staff.

## Scope

### In Scope

- **Cost categories** (tenant-managed list, seeded from an industry template; colour + icon).
- **Vendors / payees** (name, phone, email, address, notes); create inline from the cost form.
- **Cost entry** (evolves `purchase_entries`): date, category, vendor, bill/reference no., notes,
  receipt attachments (FEAT-012 files), line items with description, qty, **unit**, rate, total.
- **Vendor payment status (ADR-004 Q2):** full vendor-bill model with partial payments under the hood;
  the cost form only asks "Paid? Full / Partly / Not yet". More vendor payments can be added later.
- **Mistake-tolerant (ADR-004):** costs are editable with history, soft delete with restore, Undo toast.
- **Billable costs:** "Bill to client" toggle + markup %; creates an unbilled project charge (FEAT-029).
- **Labour quick entry:** worker/team, days or hours × rate.
- **Project P&L summary:** Revenue (charges − discount), Cost, Profit, Margin %, Paid out, We owe.
- **Cost breakdown** by category and by vendor.
- Migration of existing purchase entries into costs (category "Uncategorised").
- Audit on all cost and vendor payment actions; void instead of delete.

### Out of Scope

- Budgets and budget vs actual (FEAT-031).
- Company-wide vendor payables report (FEAT-031).
- Inventory / stock management.

## Acceptance Criteria (draft)

1. Staff can add a cost in ≤ 4 fields for the common case (amount, category, vendor, date) with an
   optional itemised mode.
2. Project shows Profit and Margin that update immediately when a cost or charge changes.
3. A cost marked "bill to client" appears as an unbilled item ready for the next invoice.
4. Costs and profit are never visible in the client portal.
