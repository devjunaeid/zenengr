---
id: TODO-014
title: Tenant plan view page
feature: FEAT-002
story: US-007
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-012]
blocks: []
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-014 — Tenant plan view page

## Description

Build read-only page for Tenant Admin showing current plan name and resource limits with usage counts.

## Acceptance criteria

- [ ] GET /api/tenant/plan returns plan details + current usage counts.
- [ ] UI shows: plan name, per-resource limit, current usage (e.g., "3/10 clients").
- [ ] No edit capability for Tenant Admin (FR-2.1 AC-3).
- [ ] Super Admin sees same data in tenant detail panel.

## Notes

