---
id: TODO-013
title: Limit enforcement middleware/service
feature: FEAT-002
story: US-007
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-012]
blocks: []
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-013 — Limit enforcement middleware/service

## Description

Build service that checks resource limits before create operations. When tenant exceeds a limit, system blocks creation and returns error. Limits apply per-tenant.

## Acceptance criteria

- [ ] Limit check service accepts tenant_id, resource type, count function.
- [ ] Called before create endpoints for admin users, clients, projects, storage.
- [ ] Returns 403 with message when limit exceeded.
- [ ] Limit values read from tenant's current Plan.
- [ ] Tenant Admin can view limits but not change them.

## Notes

