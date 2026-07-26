---
id: TODO-003
title: Author docker-compose.yml + .env.example + healthchecks
feature: FEAT-001
story: US-003
status: done
priority: high
owner: ""
estimate: ""
dependencies: [TODO-001, TODO-002]
blocks: []
created: "2026-07-25"
updated: "2026-07-25"
---

# TODO-003 — Author docker-compose.yml + .env.example + healthchecks

## Description

Create repo-root `docker-compose.yml` with services `frontend`, `backend`, `postgres`, `redis`, `pgadmin`,
including healthchecks, named volumes for `postgres` data and `pgadmin` config, depends_on ordering, env
loaded from `.env`, plus a committed `.env.example`.

## Acceptance criteria

- [ ] All five services defined and reachable from their published ports.
- [ ] `docker compose up` reaches healthy state for all services.
- [ ] pgAdmin can connect to `postgres` service.
- [ ] Backend can reach `postgres` (5432) and `redis` (6379) via service DNS.
- [ ] `.env.example` documents all required variables; `.env` git-ignored.
- [ ] Reviewed against `docs/mcp-setup.md` and `docs/code-review-checklist.md`.

## Notes