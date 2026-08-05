---
id: TODO-133
title: Logo upload + PDF branding via storage backend
feature: FEAT-012
story: US-048
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-123, TODO-126]
blocks: []
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-133 — Logo upload + PDF branding via storage backend

## Description

Rework branding to use the storage backend: logo upload endpoint stores via storage under the public namespace (`public/{tenant_id}/...`); invoice PDF reads logo via storage backend; new uploads no longer write directly to the legacy `uploads/` dir.

## Acceptance criteria

- [x] Logo upload endpoint stores via storage backend under public namespace. (FR-12.9, FR-12.2)
- [x] `branding.logo_url` points at storage-backed URL. (FR-12.9)
- [x] Invoice PDF reads logo via storage backend (get). (FR-12.9)
- [x] New uploads no longer write directly to `uploads/` dir. (FR-12.9)
- [x] Public namespace used only for branding; nothing else public. (FR-12.2)

## Notes

- Follows backfill in TODO-126 for existing logos.
- Logo upload writes public/{tenant_id} storage key; branding.logo_url -> /api/v1/public/tenant/{id}/logo; public logo endpoint (stream/redirect); PDF reads logo via storage backend.
