---
id: FEAT-012
title: File Management & Storage
status: approved
priority: P0
source: Product decision 2026-08-05
---

# FEAT-012 — File Management & Storage

## Goal

Abstraction layer for object storage (S3-compatible + local filesystem, switchable via config without code changes), per-tenant file gallery with folder organization, three visibility scopes (user-isolated, tenant-level, protected project files), secure access control for confidential project files, storage quota enforcement.

## Scope

### In Scope
- Storage abstraction: pluggable backend interface (put/get/delete/url/exists); local filesystem + S3-compatible (boto3, any endpoint_url provider: MinIO/R2/S3-compatible); switch via config (`storage_backend=local|s3`); zero code changes on switch
- Key namespacing + isolation: storage keys scoped `{tenant_id}/...`; public namespace `public/{tenant_id}/...` only for non-confidential assets (e.g. branding logo); never public for anything else; tenant isolation server-enforced on every query
- File gallery per tenant with three visibility scopes (USER/TENANT/PROJECT)
- Nested folder tree (any depth) per tenant with auto root folders per scope
- Server-side access control; 404 on unauthorized access (never 403 detail leak)
- Protected serving: auth-gated streaming (local) or short-lived presigned URL redirect (S3); PROJECT downloads audited
- Quota: per-file 25MB cap; per-tenant quota from plan max_storage_mb (413 on exceed)
- Migration/backfill tooling for legacy `uploads/` and backend transfer (local <-> s3)
- Branding integration: logo upload + invoice PDF branding via storage backend

### Out of Scope (Phase 2)
- File versioning
- Virus scanning
- Thumbnails/transcoding
- Client uploads
- Public/shared-link sharing
- S3 lifecycle policies
- Streaming large files

## Functional Requirements

- FR-12.1: Pluggable storage backend interface (`put`/`get`/`delete`/`url`/`exists`); implementations: local filesystem + S3-compatible (boto3, any `endpoint_url` provider: MinIO/R2/S3-compatible). Backend selected via config (`storage_backend=local|s3`); switching requires zero code changes.
- FR-12.2: Storage keys namespaced `{tenant_id}/...`. Public namespace `public/{tenant_id}/...` only for non-confidential assets (e.g. branding logo); never public for anything else. Tenant isolation server-enforced on every query.
- FR-12.3: Every tenant has a file gallery. Tenant staff (admin/manager/employee) can upload. Three visibility scopes: **USER** (only uploader sees), **TENANT** (all tenant staff see), **PROJECT** (protected: tenant staff with project access + client users of that project's client).
- FR-12.4: Nested folder tree (any depth) per tenant. Auto root folders per scope: "My files" (USER), "Team files" (TENANT), "Project files" (PROJECT, one subfolder per project). Nesting restricted within the same scope. Unique sibling names per parent.
- FR-12.5: Server-side access control. USER = creator only (view/download/delete own). TENANT = all staff view/download; admin/manager upload+delete+rename+move. PROJECT = all staff view/download; admin/manager upload/delete. Client users read-only for their own client's projects (`client_id == project.client_id`). Cross-tenant and cross-client access returns 404.
- FR-12.6: File content NEVER served via public static path. Local backend = auth-gated streaming endpoint. S3 backend = short-lived presigned URL (redirect). Downloads audited for PROJECT scope. Presigned URLs time-limited (default 15 min).
- FR-12.7: Per-file limit 25MB. Per-tenant quota enforced from plan `max_storage_mb` (sum of `file_assets` sizes + new upload <= quota, else 413).
- FR-12.8: Backfill script migrates legacy `uploads/` files (logo) into storage under public namespace and updates `branding.logo_url`. Tool transfers keys between backends (local <-> s3) for provider switch.
- FR-12.9: Logo upload endpoint + invoice PDF branding read/write through the storage backend (replaces direct filesystem writes).

## Acceptance Criteria

1. Upload works with a scope selector (USER/TENANT/PROJECT).
2. Folder tree operations (create/rename/delete) work.
3. User-isolated file is invisible to other users.
4. Tenant-level file is visible to all staff.
5. Project file is visible to client of that project only.
6. Download blocked for unauthorized access (404).
7. Quota exceeded returns 413.
8. Storage switch via env/config only.
9. Migration tool runnable.
10. Logo works through storage backend.

## Dependencies

- FEAT-001 (Tenant Management) — tenants own galleries; keys are tenant-scoped
- FEAT-004 (User & Access Management) — staff roles and permission matrix (`view/files`, `manage/files`)
- FEAT-005 (Client Management) — client users and `client_id` scoping for PROJECT files
- FEAT-007 (Project Management) — PROJECT scope files tied to projects

## Decisions

- All product decisions resolved 2026-08-05; no open decisions.
