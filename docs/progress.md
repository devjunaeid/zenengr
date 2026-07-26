# Progress

## Project status

- **Phase:** Setup / Design
- **Last updated:** 2026-07-25
- **Current focus:** Scaffold the local development environment (FEAT-001) before PRD-driven features.

## What changed recently

| Date | Item | Change |
| ---- | ---- | ------ |
| 2026-07-25 | `/project-init` | Ran init: detected SvelteKit + FastAPI codebase; confirmed stack with user. |
| 2026-07-25 | `docs/stack-discovery.md` | Filled from detected manifests + user answers. |
| 2026-07-25 | `docs/features/FEAT-001.md` | Replaced auth placeholder with **Local development environment** feature. |
| 2026-07-25 | `docs/stories/US-001..US-003.md` | Created FE/BE image + Compose stack stories. |
| 2026-07-25 | `docs/todos/TODO-001..TODO-003.md` | Created implementation backlog for FEAT-001. |
| 2026-07-25 | Standards docs | Populated `docs/frontend-standard.md` and `docs/backend-standard.md` from detected tooling. |
| 2026-07-25 | `docs/ui-ux-spec.md` | Set framework-agnostic defaults pending PRD. |
| 2026-07-25 | `opencode.json`, `docs/mcp-setup.md` | Enabled postgres, docker, browser MCP servers (user approved). |
| 2026-07-25 | `docs/index.md` | Refreshed dashboard with current items. |
| 2026-07-25 | TODO-001..003 | Implemented FE/BE Dockerfiles, compose stack, backend stub, switched FE to adapter-node. |
| 2026-07-25 | Dev profile | Added `frontend-dev`/`backend-dev` compose services with hot-reload mounts + profiles. |

## Completed

| Date | Item / task | Notes |
| ---- | ------------ | ----- |
| 2026-07-24 | Scaffold template files | `docs/features`, `docs/stories`, `docs/todos`, `docs/decisions`. |
| 2026-07-25 | `/project-init` completed | Stack detected and documented; FEAT-001 created. |
| 2026-07-25 | TODO-001 — Frontend Dockerfile + .dockerignore | `frontend/Dockerfile`, `frontend/.dockerignore`; switched to adapter-node for Docker. |
| 2026-07-25 | TODO-002 — Backend Dockerfile + .dockerignore + entrypoint | `backend/app/main.py`, `backend/Dockerfile`, `backend/.dockerignore`. |
| 2026-07-25 | TODO-003 — docker-compose.yml + .env.example | Repo-root `docker-compose.yml` (5 services), `.env.example`. |
| 2026-07-25 | Dev profile docker-compose | Added `frontend-dev` + `backend-dev` services with `profiles: [dev]`, volume mounts, `--reload` flag, separate Dev Dockerfiles. |

## In progress

| Date started | Item / task | Blockers | Notes |
| ------------ | ------------ | -------- | ----- |
| 2026-07-25 | FEAT-001 — Verify `docker compose up` | Docker daemon not running on this machine | Builds verified (`npm run build` + adapter-node). Verify full compose after starting Docker. |

## Blocked

| Item / task | Blocker | Owner |
| ------------ | ------- | ----- |
| FEAT-002+ (product features) | PRD not yet provided by product owner | User |

## Decisions

| Date | Decision | Rationale |
| ---- | -------- | --------- |
| 2026-07-24 | Use frontmatter-based docs | Faster context loading for agent and humans at scale. |
| 2026-07-25 | Stack: SvelteKit + JS/JSDoc + Tailwind v4 + bits-ui (FE); FastAPI + Python 3.14 + uv (BE) | Already scaffolded; confirmed by user. |
| 2026-07-25 | Backend additions: PostgreSQL + SQLAlchemy 2.0 + JWT + Alembic + pytest | User-selected over SQLite/SQLModel. |
| 2026-07-25 | Local dev via Docker Compose (FE+BE+Postgres+Redis+pgAdmin) | User request; reproducible environment. |
| 2026-07-25 | Replace scaffold auth placeholder; defer product features to PRD | User will supply PRD. |
| 2026-07-25 | Enable postgres, docker, browser MCP servers | User approved "all" MCP additions. |

## Next

1. Start Docker daemon and run `docker compose up` to verify whole stack.
2. Once PRD received, scope FEAT-002+ and the corresponding stories/todos.