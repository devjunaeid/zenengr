---
id: FEAT-001
title: Local development environment
status: proposed
priority: high
owner: ""
tags: [infra, devex, docker]
created: "2026-07-25"
updated: "2026-07-25"
---

# FEAT-001 — Local development environment

## Goal

Provide a reproducible one-command local development stack for the SvelteKit frontend, FastAPI backend, PostgreSQL database, Redis cache, and pgAdmin — bootable via `docker compose up`. This unblocks all subsequent PRD-driven feature work.

## Acceptance criteria

1. A `Dockerfile` exists for the frontend service and builds successfully with `npm run build`.
2. A `Dockerfile` exists for the backend service and runs the FastAPI app via `uv` / `uvicorn`.
3. A `docker-compose.yml` defines services: `frontend`, `backend`, `postgres`, `redis`, `pgadmin`.
4. `docker compose up` brings all services to a healthy state.
5. Frontend dev server (and/or built image) is reachable on its published port.
6. Backend FastAPI app is reachable at `/docs` (OpenAPI) on its published port.
7. PostgreSQL is reachable from the backend service via service DNS on port `5432`.
8. Redis is reachable from the backend service via service DNS on port `6379`.
9. pgAdmin is reachable in the browser and can connect to the `postgres` service.
10. Environment/secrets (DB credentials, JWT secret) are loaded from a `.env` file, not committed.

## Out of scope

- Production deployment / orchestration (host TBD).
- CI/CD pipeline (tracked separately).
- Data seeding scripts (may be filed as a follow-up TODO).

## Stories

- [US-001](../stories/US-001.md) — Frontend Docker image
- [US-002](../stories/US-002.md) — Backend Docker image
- [US-003](../stories/US-003.md) — Compose stack with all services

## Notes

- This feature is the only confirmed actionable requirement at phase `Design`. PRD-driven product features will be filed as FEAT-002+ once the PRD is provided.