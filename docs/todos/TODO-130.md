---
id: TODO-130
title: Download API + protected serving
feature: FEAT-012
story: US-051
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-128]
blocks: [TODO-132, TODO-135]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-130 — Download API + protected serving

## Description

Auth-gated download endpoint: local backend streams content; S3 backend redirects to short-lived presigned URL (default 15 min). Access rules: tenant staff + client users of the file's project client. PROJECT scope downloads audited. Content never on a public static path.

## Acceptance criteria

- [x] GET file content endpoint auth-gated; local backend streams content. (FR-12.6)
- [x] S3 backend redirects to short-lived presigned URL (default 15 min). (FR-12.6)
- [x] Content never served from public static path. (FR-12.6)
- [x] PROJECT scope downloads audited. (FR-12.6)
- [x] Access rules: staff + client users of the file's project client (`client_id == project.client_id`). (FR-12.5)
- [x] Unauthorized access returns 404 (no detail leak). (FR-12.5)

## Notes

- Needs S3 presign support from TODO-124.
- GET /{id}/content auth-gated: local stream bytes or S3 presigned 307 redirect; PROJECT downloads audited.
