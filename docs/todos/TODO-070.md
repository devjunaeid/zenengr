---
id: TODO-070
title: Soft removal logic for invoiced services
feature: FEAT-007
story: US-028
status: done
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

- [x] DELETE /api/tenant/projects/{id}/services/{service_id} checks for invoice line items.
- [x] If invoiced: set ProjectService.status=Cancelled (soft delete) (FR-7.6).
- [x] If not invoiced: hard delete ProjectService + milestones.
- [x] Cancelled services clearly marked in project view (TODO-071).
- [x] Financial records referencing cancelled service intact (FR-7.6).

## Notes

DELETE /api/v1/tenant/projects/{project_id}/services/{project_service_id} (manage/projects): any invoice line-item reference -> soft cancel (ProjectServiceStatus.CANCELLED, milestones + financial records intact); none -> hard delete with milestones. Already-cancelled -> 409. Cancelled indicator UI already shipped (TODO-071).

