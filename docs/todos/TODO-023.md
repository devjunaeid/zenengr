---
id: TODO-023
title: Runtime flag check middleware
feature: FEAT-003
story: US-011
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-020]
blocks: [TODO-025]
created: "2026-07-26"
updated: "2026-07-27"
---

# TODO-023 — Runtime flag check middleware

## Description

Build middleware/service that checks feature flag before allowing API access. Disabled feature endpoints return 403/404. UI hiding is secondary.

## Acceptance criteria

- [ ] Flag check service: is_feature_enabled(tenant_id, flag_key) -> bool.
- [ ] Decorator/permission dependency for FastAPI endpoints gated by flag key.
- [ ] Disabled feature returns 403 with descriptive message.
- [ ] Flag changes take effect on next request (no cache, or short TTL).
- [ ] Tenant Admin views enabled/disabled features but cannot toggle (FR-3.4).

## Notes

