---
id: TODO-056
title: Service model + milestone step template model
feature: FEAT-006
story: US-023
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-004]
blocks: [TODO-057, TODO-058, TODO-059, TODO-062]
created: "2026-07-26"
updated: "2026-07-31"
---

# TODO-056 — Service model + milestone step template model

## Description

Create Service model and MilestoneStepTemplate model. Service has name, description, default price. Each service has ordered milestone steps with name, sequence, optional duration, description.

## Acceptance criteria

- [x] Service model: id, tenant_id FK, name, description, default_price, is_active, timestamps.
- [x] MilestoneStepTemplate model: id, service_id FK, name, sequence_order, expected_duration_days, description, timestamps.
- [x] Alembic migration creates both tables.
- [x] Different services can have different milestone structures (FR-6.3).
- [x] CASCADE delete of service deletes its step templates.

## Notes

