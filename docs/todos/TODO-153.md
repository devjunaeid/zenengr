---
id: TODO-153
title: General invoice create/update/list support
feature: FEAT-015
story: US-056
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-152]
blocks: [TODO-159]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-153 - General invoice create/update/list support

## Description

Service + API accept project XOR client XOR neither. General invoices require custom line items only. Staff-only; client portal + rollups exclude naturally (no project/client linkage).

## Acceptance criteria

- [x] API accepts project XOR client XOR neither on create/update. (FR-15.1)
- [x] General invoices require custom line items only. (FR-15.1)
- [x] General invoices staff-only; never in client portal or client rollups. (FR-15.1, FR-15.7)
- [x] Same gapless numbering; drafts/issue/void behave like project invoices. (FR-15.1)

## Notes

- Shipped: general invoice create/update/list - project XOR client XOR neither, custom items only, staff-only, excluded from portal + rollups, same gapless numbering.
