---
id: TODO-124
title: S3-compatible storage backend (boto3, presigned URLs)
feature: FEAT-012
story: US-048
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-123]
blocks: [TODO-130]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-124 — S3-compatible storage backend (boto3, presigned URLs)

## Description

Create `S3StorageBackend` via boto3: client built from settings (`endpoint_url`, access/secret key, bucket); implement put/get/delete/exists; `url()` returns presigned GET with expiry + download disposition. Tests with moto or a fake.

## Acceptance criteria

- [x] boto3 client built from settings: endpoint_url, access/secret key, bucket. (FR-12.1)
- [x] put/get/delete/exists implemented against S3. (FR-12.1)
- [x] `url()` returns presigned GET with expiry (default 15 min) + download disposition. (FR-12.6)
- [x] Works with any endpoint_url provider (MinIO/R2/S3-compatible). (FR-12.1)
- [x] Tests with moto or a fake S3. (FR-12.1)

## Notes

- Presigned URLs time-limited (default 15 min). (FR-12.6)
- Blocked by TODO-123 (protocol + factory).
- S3StorageBackend via boto3 (endpoint_url for MinIO/R2), presigned GET URLs with expiry + download disposition; moto-tested.
