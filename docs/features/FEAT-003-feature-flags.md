---
id: FEAT-003
title: Feature Flags
status: approved
priority: P0
source: docs/prd.md §6.3
---

# FEAT-003 — Feature Flags

## Goal

Provide Super Admin with per-tenant feature flag control. Flags are data-driven, take effect without redeployment, and are not self-service by tenants. Flags enable gating of Phase 2 capabilities at the tenant level.

## Scope

### In Scope
- Super Admin enable/disable feature flags per tenant (key-value/boolean registry)
- Application checks flags before rendering/allowing functionality
- Default flag values per Plan with Super Admin override per tenant
- Tenant-side read-only view of enabled/disabled flags with optional "request upgrade" prompt
- Data-driven flag loading (no code changes or redeploy required for flag toggle)

### Out of Scope
- Self-service flag enablement by Tenant Admin (FR-3.4 explicitly forbids)
- Online payment collection — gated behind `client_portal_payments` flag, NOT built in MVP (Phase 2)
- Milestone-triggered auto-invoicing — gated behind a future flag (Phase 2)

## Functional Requirements

- FR-3.1: Super Admin can enable/disable individual **feature flags** per tenant (e.g., `client_portal_payments`, `multi_service_projects`, `comments_module`, `partial_payment_tracking`).
- FR-3.2: Feature flags should be structured as a simple key-value/boolean registry per tenant, checked by the application before rendering/allowing the related functionality.
- FR-3.3: Feature flags may optionally have a default value per Plan (e.g., Starter plan defaults `custom_branding = false`), but Super Admin can override the default per individual tenant.
- FR-3.4: Tenant-side users (including Tenant Admin) cannot self-enable a disabled feature; they can only see current capability status and (optionally) a "request upgrade" prompt.
- FR-3.5: Feature flag changes should take effect without requiring redeployment (data-driven, not code-driven).

## Acceptance Criteria

1. Super Admin can view a list of all feature flags for a tenant with current on/off state.
2. Super Admin can toggle a flag on/off for a specific tenant; change takes effect immediately on next request.
3. A feature gated by a disabled flag is hidden from the UI and rejected by the API for that tenant.
4. Tenant Admin can view the list of enabled/disabled features but cannot toggle any flag.
5. Plan-level default flags apply when a new tenant is created with a given Plan.
6. Super Admin override per tenant persists independently of Plan defaults.
7. Adding a new flag key to the database makes it available immediately without code deploy.

## Dependencies

- FEAT-001 (Tenant Management) — flags are per-tenant
- FEAT-002 (Subscription & Settings) — flag defaults are per-Plan

## Decisions

- **Flags are data-driven, effective without redeploy.**
- **Online payment collection** is a Phase 2 flag (`client_portal_payments`), NOT built in MVP.
