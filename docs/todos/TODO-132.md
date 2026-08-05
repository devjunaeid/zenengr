---
id: TODO-132
title: Client portal file access
feature: FEAT-012
story: US-051
status: done
priority: P0
owner: ""
estimate: ""
dependencies: [TODO-130]
blocks: [TODO-135]
created: "2026-08-05"
updated: "2026-08-05"
---

# TODO-132 — Client portal file access

## Description

Client Portal endpoints: GET project files scoped to the client's own projects + GET file content endpoint. Read-only for client users; any other client's files return 404.

## Acceptance criteria

- [x] GET /client/projects/{id}/files lists PROJECT files for own client. (FR-12.5)
- [x] GET /client/files/{id}/content streams/downloads file (own client only). (FR-12.5)
- [x] Read-only: no upload/rename/delete for client users. (FR-12.5)
- [x] Other client's files return 404. (FR-12.5)
- [x] PROJECT scope downloads audited. (FR-12.6)

## Notes

- Client access rule: `client_id == project.client_id`.
- GET /client/projects/{id}/files + /client/files/{id}/content; PROJECT scope only, project.client_id == user.client_id, read-only, downloads audited CLIENT_USER.
