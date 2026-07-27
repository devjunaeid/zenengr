---
id: ADR-003
title: MVP scope decisions
status: accepted
date: "2026-07-26"
owner: ""
tags: [mvp, scope, architecture]
---

# ADR-003 — MVP scope decisions

## Context

During product feature scoping for the MVP, several design and scope decisions were confirmed by stakeholders to keep the MVP buildable while preserving a clear upgrade path for Phase 2 capabilities.

## Decision

### 1. Super Admin is strictly container-level

Super Admin has NO access to tenant operational data (clients, projects, invoices) and NO impersonation of tenant users in MVP. This keeps data isolation simple and avoids needing fragile cross-tenant access controls.

### 2. MVP payments are manually recorded by staff

Online payment gateway collection is Phase 2 behind the `client_portal_payments` feature flag. Staff record payments manually (bank transfer, card, cash, other) into the system.

### 3. Payment allocation: system proposes proportional/FIFO, staff may override

When an invoice has multiple line items, the system proposes a proportional or FIFO auto-allocation of a payment across line items. Staff can manually override the allocation per line item.

### 4. One Client User login is scoped to exactly one tenant relationship

A Client User's login is bound to a single Client record within one tenant. Cross-tenant or multi-Client scoping is not supported in MVP.

### 5. Milestone statuses fixed enum; sequential completion not enforced

Milestone statuses are: Pending, In Progress, Completed, Blocked. Project milestones may be completed in any order — strict sequential completion is NOT enforced.

### 6. Invoice numbering: tenant-scoped gapless sequential with configurable format

Each tenant has a configurable invoice number format template (e.g. INV-2026-0001). Numbers are assigned sequentially and gapless per tenant at the moment of issuance.

### 7. Core invoicing model (per PRD §7)

- Project-to-Invoice is 1-to-N (one project has many invoices over its lifetime).
- Draft invoices are fully editable; Issued invoices are immutable (core financial fields locked).
- Mid-project service additions bill via a new invoice (never reopen an issued invoice).
- Financial rollups (Total Invoiced, Total Paid, Total Outstanding) are computed from live data, not stored.

## Consequences

- Phase 2 will add online payment gateway, credit notes, milestone-triggered auto-invoicing, and Super Admin impersonation — all behind feature flags.
- Data model must support the configurable invoice number format from the start.
- Payment allocation UI must support both auto-proposal and manual override per line item.
- Client Portal is single-tenant-scoped only; no multi-tenant Client User concept in MVP.
