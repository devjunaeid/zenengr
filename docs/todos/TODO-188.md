---
id: TODO-188
title: Live statement preview & PDF export API
feature: FEAT-019
story: US-063
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-187]
blocks: [TODO-190, TODO-191]
created: "2026-08-26"
updated: "2026-08-26"
---

# TODO-188 — Live statement preview & PDF export API

## Description

Create endpoints:
- `GET /api/v1/tenant/projects/{id}/statement`: Returns the current chronological statement JSON (entries, totals, due, advance credit).
- `GET /api/v1/tenant/projects/{id}/statement/pdf`: Generates on-the-fly statement PDF marked "LIVE STATEMENT" without issuing an invoice.

## Acceptance criteria

- [ ] Returns structured statement data for staff users.
- [ ] Returns rendered PDF bytes for live statement printing.
- [ ] Strictly tenant-isolated.
