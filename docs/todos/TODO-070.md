---
id: TODO-070
title: Soft removal logic for invoiced services
feature: FEAT-007
story: US-028
status: proposed
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-062, TODO-075]
blocks: [TODO-071]
created: "2026-07-26"
updated: "2026-07-26"
---

# TODO-070 — Soft removal logic for invoiced services

## Description

Implement service removal from project: if service has invoice references, mark as Cancelled (soft removal). If no invoices, delete entirely.

## Acceptance criteria

- [ ] DELETE /api/tenant/projects/{id}/services/{service_id} checks for invoice line items.
- [ ] If invoiced: set ProjectService.status=Cancelled (soft delete) (FR-7.6).
- [ ] If not invoiced: hard delete ProjectService + milestones.
- [ ] Cancelled services clearly marked in project view (TODO-071).
- [ ] Financial records referencing cancelled service intact (FR-7.6).

## Notes

