---
id: TODO-014
title: Tenant plan view page
feature: FEAT-002
story: US-007
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-012]
blocks: []
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-014 — Tenant plan view page

## Description

Build read-only page for Tenant Admin showing current plan name and resource limits with usage counts.

## Acceptance criteria

- [x] GET /api/tenant/plan returns plan details + current usage counts.
- [x] UI shows: plan name, per-resource limit, current usage (e.g., "3/10 clients").
- [x] No edit capability for Tenant Admin (FR-2.1 AC-3).
- [ ] Super Admin sees same data in tenant detail panel.

## Notes

- AC4 (SA plan detail panel) not yet met: `admin/tenants/[id]/+page.svelte` only renders plan name + status, no limits/usage table. Link to plan-level view or extend SA panel in a later batch.

