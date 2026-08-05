---
id: TODO-146
title: Wire settings into staff + client layouts
feature: FEAT-014
story: US-055
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-145]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-146 - Wire settings into staff + client layouts

## Description

Load tenant formatting settings once per session in layouts: `app/+layout.js` loads via tenantApi (`GET /tenant/settings`); client layout loads via the new client settings endpoint (`GET /client/settings`). Both call `setTenantSettings` to populate the store.

## Acceptance criteria

- [x] `app/+layout.js` loads settings via tenantApi and calls `setTenantSettings`. (FR-14.1)
- [x] Client portal layout loads via `GET /client/settings` and calls `setTenantSettings`. (FR-14.1)
- [x] Settings loaded once per session. (FR-14.1)

## Notes

- Depends on frontend settings store (TODO-145) and, for the client layout, on the client settings endpoint (TODO-147).
- Shipped 2026-08-05: staff app/+layout.js loads via `GET /tenant/settings`, client layout via `GET /client/settings`; both call setTenantSettings once per session.
