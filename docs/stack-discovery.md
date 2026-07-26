# Stack Discovery

Filled by `/project-init`. Detected from existing codebase and confirmed by user.

## Basic project info

- **Project name:** zenengr
- **One-line description:** _TBD — pending PRD from product owner._
- **Domain / industry:** _TBD — pending PRD._
- **Current phase:** Design

## Team & delivery

- **Solo or team?** _TBD
- **Deployment target:** Self-hosted (target production TBD). Local dev uses Docker Compose.
- **CI/CD:** GitHub Actions (to be configured).

## Frontend

- **Framework:** SvelteKit 2 (Svelte 5, runes mode enforced)
- **Language:** JavaScript with JSDoc (no TypeScript per `frontend/AGENTS.md`)
- **Styling:** Tailwind CSS v4 (via `@tailwindcss/vite`)
- **Component library:** bits-ui
- **Content addons:** `@tailwindcss/forms`, `@tailwindcss/typography`
- **State management:** TBD — Svelte stores / runes by default
- **Data fetching:** SvelteKit `load` functions / `fetch` from `event.fetch`
- **Testing:** TBD — none configured yet
- **Package manager:** npm
- **Adapter:** `@sveltejs/adapter-auto`
- **Tooling:** ESLint + eslint-config-prettier + eslint-plugin-svelte; Prettier with prettier-plugin-svelte + prettier-plugin-tailwindcss; svelte-check

## Backend

- **Runtime / language:** Python 3.14
- **Framework:** FastAPI (with `[standard]` extras / `fastapi[standard]`)
- **Package manager:** uv (`uv.lock`)
- **Database:** PostgreSQL
- **ORM / query builder:** SQLAlchemy 2.0 (to be added)
- **Authentication:** JWT (to be added)
- **Validation:** Pydantic v2 (built into FastAPI)
- **API style:** REST
- **Testing:** pytest (to be added)

## Infrastructure (local dev)

- Docker per-service images: `frontend/`, `backend/`
- Docker Compose stack: frontend, backend, PostgreSQL, Redis, pgAdmin
- Production deploy target TBD (self-hosted)

## Product requirements

- **Core problem being solved:** _TBD — pending PRD._
- **Primary users:** _TBD — pending PRD._
- **Must-have features (top 3–5):** _TBD — pending PRD._ User indicated "all of these" candidate areas (auth/accounts/dashboard/API, notes/tasks, real-time chat, admin/data management) will be scoped from PRD.
- **Explicitly out of scope:** _To be specified manually by user._

## Existing codebase

- **Does an existing codebase exist?** Yes
- **Repository structure summary:**
  - `frontend/` — SvelteKit app (routes, lib) — scaffolded; minimal pages.
  - `backend/` — FastAPI app — only `pyproject.toml` + `.venv`; no source yet.
  - `docs/` — this scaffold's documentation tree.
- **Known tech debt or constraints:** Backend has no source code yet. Frontend is freshly scaffolded. Auth feature file present in scaffold is a placeholder and will be replaced by PRD-derived features.

## MCP / tools

- **Git integration needed?** Yes (configured in `opencode.json`).
- **Database MCP needed?** Yes (PostgreSQL) — to be added.
- **Browser automation needed?** Yes (Puppeteer) — to be added.
- **Docker MCP needed?** Yes (container management) — to be added.
- **Issue tracker:** GitHub Issues (GitHub MCP already configured).

## Decisions log

| Date | Decision | Rationale |
| ---- | -------- | --------- |
| 2026-07-25 | Adopt SvelteKit + Svelte 5 (runes) frontend | Already scaffolded; user confirmed. |
| 2026-07-25 | Adopt FastAPI + Python 3.14 + uv backend | Already scaffolded; user confirmed. |
| 2026-07-25 | Add PostgreSQL + SQLAlchemy 2.0 + JWT | User selected over SQLite/SQLModel. |
| 2026-07-25 | Local dev via Docker Compose (FE+BE+PG+Redis+pgAdmin) | User request; enables reproducible environment. |
| 2026-07-25 | Phase set to Design; PRD-driven features deferred | User will supply PRD before feature scoping. |
| 2026-07-25 | Enable Postgres, Docker, Browser MCP servers | User approved "all" MCP additions. |