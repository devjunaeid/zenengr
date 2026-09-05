# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Tenants** — service-based businesses (agencies, consultancies, studios). Their staff run operations:
  - **Tenant Admin**: full control within the tenant — users, clients, services, projects, invoices, settings (within Super Admin allowances).
  - **Tenant Manager**: operational work (services, projects, milestones, invoices), typically excluded from billing and user-role management.
  - **Tenant Employee**: works assigned projects/milestones; limited financial visibility.
- **Client Users** — the tenant's own customers. Log into a separate, strictly-scoped Client Portal to track project progress, view invoices/payments, access shared files, and comment.
- **Super Admin** — platform operator. Manages tenants, subscriptions, feature flags. By design has **no** access to tenant operational data.

## Product Purpose

A multi-tenant SaaS platform where service businesses sell **Services** with milestone-based delivery, bundle them into **Projects**, **invoice** clients (including mid-project scope growth), and track **payments** — partial, per-line-item, and advance/ledger-based. Success for MVP: a tenant can run the full loop — create client → define service with milestone template → create project → track milestones → issue invoices → record payments → client sees everything in their portal.

## Positioning

Milestone-template services with **balance-forward project ledgers**: issued invoices are immutable (scope growth bills via new invoices), payments allocate across line items, advances/ledger transactions net against project charges, and a Super Admin entitlement layer (plans + per-tenant feature flags) governs it all — with strict tenant data isolation underneath.

## Operating Context

- Two separate auth realms and portals: **Admin/Ops Portal** (`/app`, `/admin`) and **Client Portal** (`/client`).
- Dev stack runs in Docker (Postgres, Redis, MailHog at :8025, backend :8000, frontend :5173) — see `AGENTS.md`.
- Per-tenant SMTP for outgoing email; MailHog captures it in dev.
- Tenant-wide currency, date/time format, and timezone formatting applied across both portals and PDFs.

## Capabilities and Constraints

Confirmed (from `docs/prd.md` v0.1, implemented FEAT-001..018):

- Tenant provisioning, plans with data-driven limits, per-tenant feature flags (runtime-checked, no redeploy).
- Custom roles + permission matrix, RBAC enforced server-side; last-admin guard; soft-delete users.
- Service catalog with milestone step templates — templates never mutate already-instantiated project milestones.
- Projects bundle services; mid-life scope growth adds services; invoiced services are soft-cancelled, never deleted.
- Invoice lifecycle Draft → Issued (locked) → Partially Paid → Paid / Void; tenant-scoped sequential numbering; PDF export.
- Partial payments with proportional/FIFO auto-allocation plus manual override; advances, ledger transactions (debit/credit/refund), general invoices; project ledger balance-forward.
- Audit trail on sensitive actions; realtime (WebSocket) notifications in both portals; file storage (local/S3-compatible) with quota.
- Comments per project with internal-only vs shared visibility.

MVP constraints: single currency per tenant, manual payment recording (gateway = Phase 2), milestone completion does NOT auto-invoice, fixed milestone status enum (Pending/In Progress/Completed/Blocked), no native mobile apps.

Explicitly undecided (Phase 2 candidates, per `docs/index.md`): per-client billing modes, credit notes, automatic advance application, multi-currency, online payment gateway, client uploads, public share links, i18n.

## Brand Commitments

- Product name **"Zenengr"** is final (user-confirmed 2026-08-28).
- No formal brand assets (logo, voice guide, kit) exist yet — do not assume any.

## Evidence on Hand

- `docs/prd.md` — BRD v0.1, source of truth. `docs/features/`, `docs/stories/`, `docs/decisions/ADR-003-mvp-scope-decisions.md`, `docs/ui-ux-spec.md`, `docs/index.md`, `docs/progress.md`.
- **Pre-launch: no real tenants, customers, testimonials, or usage data exist. Future design work must not fabricate any.**

## Product Principles

1. **Tenant isolation is absolute** — every record, query, and view is tenant-scoped; no cross-tenant leakage under any tenant-side role.
2. **Financial history is immutable once finalized** — corrections create new records; never reopen or destroy issued ones.
3. **Entitlements are data-driven** — plans and feature flags control capability per tenant, never code forks.
4. **Two audiences, two realms** — staff operations and client self-service stay strictly separated, visually and functionally.
5. **Client portal stays minimal** — progress, invoices, files, comments; nothing that adds cognitive load for customers.

## Accessibility & Inclusion

- Solid accessibility basics expected of all UI (labels, focus states, contrast, keyboard paths), but no formal certification standard (e.g. WCAG AA) is required. User-confirmed 2026-08-28.
