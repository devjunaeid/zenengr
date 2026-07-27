---
id: FEAT-002
title: Subscription & Settings
status: approved
priority: P0
source: docs/prd.md §6.2
---

# FEAT-002 — Subscription & Settings

## Goal

Provide Super Admin with control over tenant subscription plans and operational settings. Plans define resource limits; settings configure tenant-specific operational behavior. Both are data-driven for flexibility without code changes.

## Scope

### In Scope
- Super Admin assignment of subscription Plans to tenants (Free/Trial, Starter, Pro, Enterprise)
- Data-driven plan limits (max users, clients, projects, storage)
- Super Admin view/edit of subscription status, billing cycle, renewal date (manually tracked in MVP)
- Tenant Settings: default currency, invoice numbering format, timezone, date format, email sender identity
- Permission table per setting: Super Admin only / Tenant Admin editable / Tenant Admin viewable

### Out of Scope
- Automated billing of tenants by the platform (Phase 2)
- Payment gateway integration for tenant subscription fees (Phase 2)
- Self-service plan upgrades/downgrades by Tenant Admin (Phase 2 candidate)

## Functional Requirements

- FR-2.1: Super Admin can assign a subscription **Plan** to a tenant (e.g., Free/Trial, Starter, Pro, Enterprise).
- FR-2.2: Each Plan defines default limits (e.g., max admin users, max clients, max active projects, max storage) — MVP can ship a small set of plans; limits should be data-driven, not hardcoded in code, so Super Admin can adjust them.
- FR-2.3: Super Admin can view/edit a tenant's subscription status (active, past due, cancelled), billing cycle, and renewal date. (MVP: manually tracked by Super Admin; automated billing of tenants is Phase 2.)
- FR-2.4: Tenant Settings (distinct from subscription) include operational configuration such as default currency, invoice numbering format, timezone, date format, email sender identity, etc. Some settings are editable by Tenant Admin; others are Super-Admin-only.
- FR-2.5: A clear permission table must define, per setting, whether it is `Super Admin only`, `Tenant Admin editable`, or `Tenant Admin viewable only`.

## Acceptance Criteria

1. Super Admin can create, edit, and delete subscription Plans with custom limit fields.
2. Super Admin can assign a Plan to a tenant and view current subscription status.
3. Tenant Admin can view their own subscription plan and limits but cannot change them.
4. Tenant Admin can edit settings flagged as "Tenant Admin editable" (e.g., invoice numbering format, timezone).
5. Tenant Admin can view but not edit settings flagged as "Super Admin only" (e.g., email sender identity).
6. Plan limit enforcement: when a tenant exceeds a limit (e.g., max users), the system blocks further creation and shows an error.
7. Invoice numbering respects the tenant's configured format template (e.g., INV-2026-0001) and is tenant-scoped gapless sequential.

## Dependencies

- FEAT-001 (Tenant Management) — tenant must exist before subscription/settings can be assigned

## Decisions

- **Plans are data-driven, not hardcoded.** Super Admin adjusts limits via the admin UI.
- **Invoice numbering:** tenant-scoped gapless sequential with configurable format template (e.g. INV-2026-0001).
- **FR-2.5 permission table** (per-setting: Super Admin only / Tenant Admin editable / Tenant Admin viewable) must be implemented in the settings UI.
