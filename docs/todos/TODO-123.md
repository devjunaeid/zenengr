---
id: TODO-123
title: Storage backend protocol + local implementation + config factory
feature: FEAT-012
story: US-048
status: done
priority: P0
owner: ""
estimate: ""
dependencies: []
blocks: [TODO-124, TODO-125, TODO-126, TODO-133]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-123 — Storage backend protocol + local implementation + config factory

## Description

Create the storage abstraction layer: `StorageBackend` protocol with `put`/`get`/`delete`/`url`/`exists`; `LocalStorageBackend` storing under a configured directory; settings `storage_backend` (local|s3) + `storage_local_dir`; `create_storage` factory returning the backend selected by config.

## Acceptance criteria

- [x] StorageBackend protocol: put, get, delete, url, exists. (FR-12.1)
- [x] LocalStorageBackend stores files under configured directory (`storage_local_dir`). (FR-12.1)
- [x] Settings: `storage_backend` (local|s3) + `storage_local_dir`. (FR-12.1)
- [x] `create_storage` factory returns backend from settings; switching backend = config change only. (FR-12.1)
- [x] Unit tests for protocol + local backend (roundtrip put/get/delete/exists/url). (FR-12.1)

## Notes

- `url()` for the local backend returns a reference to the auth-gated streaming route; never a public static path. (FR-12.6)
- Local backend is the default dev choice.
- StorageBackend protocol; LocalStorageBackend; storage_backend/storage_local_dir config; create_storage factory; docker-compose storage_data volume.
