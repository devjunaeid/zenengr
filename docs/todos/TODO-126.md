---
id: TODO-126
title: Storage migration/backfill tool
feature: FEAT-012
story: US-048
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-123, TODO-125]
blocks: [TODO-133]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-126 — Storage migration/backfill tool

## Description

Build the storage migration tool: backfill script migrates legacy `uploads/` files (logo) into storage under the public namespace and updates `branding.logo_url`; a transfer tool moves keys between backends (local <-> s3) for provider switch.

## Acceptance criteria

- [x] CLI/script backfills legacy `uploads/` files into storage public namespace. (FR-12.8)
- [x] Logo file migrated to `public/{tenant_id}/` branding path; `branding.logo_url` updated. (FR-12.8)
- [x] Transfer tool moves keys between backends (local <-> s3). (FR-12.8)
- [x] Runs as an ops tool; no app code changes required. (FR-12.8)
- [x] Idempotent or documented rerun behavior. (FR-12.8)

## Notes

- Depends on TODO-123 (backends) + TODO-125 (branding model access).
- scripts/migrate_storage.py: backfill-legacy (uploads/ logos -> public/{tenant_id} namespace, updates branding) + transfer local<->s3 (keys identical, DB untouched).
