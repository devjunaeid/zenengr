---
id: TODO-184
title: Discount editor UI
feature: FEAT-018
story: US-061
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-181]
blocks: [TODO-186]
created: "2026-08-07"
updated: "2026-08-07"
---

# TODO-184 - Discount editor UI

## Description

Project detail discount control (admin/manager only): type select + value input, shows computed discount amount live, clear option. Audit trail visible via existing audit log. Never rendered on client timeline.

## Acceptance criteria

- [x] Discount control on project detail: admin/manager only; type select + value; live computed discount amount. (FR-18.3)
- [x] Clear (null) supported; audit trail via existing audit log. (FR-18.3)
- [x] Discount never shown on client timeline. (FR-18.3)

## Notes

- Shipped: discount editor + adjustment dialogs; discount never on client timeline.
