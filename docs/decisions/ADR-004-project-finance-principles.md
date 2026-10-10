---
id: ADR-004
title: Project finance principles - flexible, mistake-tolerant, auditable
status: accepted
date: "2026-10-10"
owner: "User"
tags: [finance, ux, audit, invoicing, payments, costs]
---

# ADR-004 - Project finance principles

## Context

The 2026-10-10 financial review (FEAT-027..031) left six open decisions. The user's direction:
"Follow best industry standard, but UX and flexibility come first. Users will make mistakes, so the
system must be flexible enough to fix them, and the admin flow must be easy for any non-technical
person."

Reference products: QuickBooks Online, Xero, Zoho Books, FreshBooks, Procore/Buildertrend (construction).

## Decision

### Guiding principle: "Fix anything, lose nothing"

Industry tools do not make users void-and-re-enter to fix a typo. They allow edits and keep a
complete history. We adopt the same model:

1. **Everything is editable while it makes sense**, including amounts, dates, methods, allocations,
   costs and adjustments. Each edit stores a full before/after version (`audit_log`), visible as
   "History" on the record.
2. **Delete = soft delete (void) with Undo.** Deleted/voided records stay in history, are excluded
   from totals, and can be **restored** by an admin. A reason is *optional* (prompted, not forced) for
   payments/adjustments; it is *required* only for voiding an issued invoice.
3. **Undo toast** (≈8 s) after create/edit/delete of financial records.
4. **Issued invoices are editable** (Zoho/QBO style) with revision history; the PDF shows the latest
   revision. If edits drop the total below the amount already paid, the excess automatically becomes
   client advance. A credit note remains available for formal corrections after the client has
   accepted an invoice.
5. **Protection comes from the period lock, not from rigidity.** Records dated on/before a "books
   locked" date cannot be changed without an audited unlock (FEAT-031). Default: no lock.
6. **Validation is friendly, not blocking:** warnings for unusual input (e.g. payment larger than
   due → "This will create an advance of X. Continue?"), hard errors only for impossible states
   (negative amounts, over-allocation).
7. **Plain language everywhere**; accounting terms only in exports.

### Resolved open questions

| # | Question | Decision (industry standard, UX first) |
|---|---|---|
| Q1 | Tax/VAT | Optional, **off by default**. Tenant defines named tax rates (e.g. "VAT 15%"); default rate auto-applied, changeable **per line**; tax-exclusive by default with an inclusive toggle per invoice. |
| Q2 | Vendor payments | Full **vendor bill** model with partial payments under the hood (Xero/QBO "Bills"), but the cost form only asks **"Paid? Full / Partly / Not yet"**. Partial payments can be added later. |
| Q3 | Budgets | **Per cost category** by default; optional line-level breakdown (BOQ) when the user expands a category. |
| Q4 | Retention | Supported, **optional per project** (off by default), % withheld per invoice, released via a "Release retention" invoice. |
| Q5 | Data migration | **Yes**: dry-run reconciliation report first, originals retained, idempotent commit. |
| Q6 | Client portal | Clients see invoices, statement, their payments and milestone progress. **Never** costs, vendors, budgets or profit. |

## Consequences

- FEAT-027 FR-27.6 / FR-27.9 / US-078 changed from "void + re-record" to "edit with history + soft
  delete with restore".
- A shared `record history` UI component and versioned audit details are needed.
- Period lock (FEAT-031) becomes the main integrity control; recommend it in onboarding for
  companies with accountants.
- Reports must always exclude voided records and use current revisions.
