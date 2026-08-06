---
id: TODO-165
title: Roles management UI
feature: FEAT-016
story: US-058
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-163]
blocks: []
created: "2026-08-06"
updated: "2026-08-06"
---

# TODO-165 - Roles management UI

## Description

Roles page: role list, toggle switches grouped by resource, create/delete custom roles, reset defaults; admin role shown as "Full tenant access" with always-on/disabled toggles (immutable).

## Acceptance criteria

- [x] Roles list page with permission toggle switches grouped by resource. (FR-16.6)
- [x] Create + delete custom roles; delete guard (unassigned only). (FR-16.6)
- [x] Admin role shown as "Full tenant access", toggles always-on/disabled, not deletable/renamable. (FR-16.3)
- [x] Reset-defaults action. (FR-16.6)

## Notes

- Toggles editable only for manager / employee / custom roles. (FR-16.3)
- Shipped: Roles page - toggle switches grouped by resource, admin "Full tenant access" immutable, create/delete custom roles, reset defaults.
