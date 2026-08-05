---
id: TODO-152
title: Invoice project_id/client_id nullable + migration
feature: FEAT-015
story: US-056
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-153]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-152 - Invoice project_id/client_id nullable + migration

## Description

Make `Invoice.project_id` and `Invoice.client_id` nullable via migration. General invoice rows have both NULL (tenant-internal billing: internal works/misc charges). Existing queries unaffected.

## Acceptance criteria

- [x] project_id and client_id nullable on Invoice. (FR-15.1)
- [x] General invoice rows have both columns NULL. (FR-15.1)
- [x] Migration present; existing queries unaffected. (FR-15.1)

## Notes

- Shipped: migration f9a0b1c2d3e4 makes project_id/client_id nullable; general invoices have both NULL.
