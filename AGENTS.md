# AGENTS.md

This file provides guidance to opencode when working with code in this repository.

## Repository purpose

This is an **agentic development scaffold/template**. It is not an application codebase by itself; it provides the documents, configuration, and conventions to bootstrap AI-driven development on a new or existing project.

When a developer clones this template and runs the `/project-init` command, opencode should:

1. Read `Agent.md` and the `docs/` files it lists.
2. Prompt the developer (or scan the existing codebase) to discover the tech stack.
3. Update/derive the following docs to match the actual project:
   - `docs/index.md` — Project dashboard / index
   - `docs/features/` — Product Requirements Document split by feature
   - `docs/stories/` — User stories
   - `docs/todos/` — Implementation backlog
   - `docs/progress.md` — Development progress tracker
   - `docs/ui-ux-spec.md` — UI/UX specification (frontend)
   - `docs/frontend-standard.md` — Frontend coding standards
   - `docs/backend-standard.md` — Backend coding standards
4. Suggest or configure required MCP servers and opencode skills/commands, and update `opencode.json` and `.opencode/` as needed.
5. Never treat the scaffold's own files as the product being built unless the user explicitly says so.

## Key files and where to look

| File / directory | Purpose |
| ---------------- | ------- |
| `Agent.md` | Root agent instruction. Always read this first. It defines context files, skills, and workflow. |
| `docs/` | All project documentation lives here: PRD, user stories, progress, todos, standards, UI/UX spec. |
| `docs/index.md` | Auto-generated project dashboard; starting point for status. |
| `docs/features/*.md` | Product requirements, one file per feature. |
| `docs/stories/*.md` | User stories, one file per story. |
| `docs/todos/*.md` | Implementation backlog, one file per task. |
| `docs/progress.md` | Living progress tracker; update after each implementation session. |
| `docs/frontend-standard.md` | Frontend conventions: framework, styling, component patterns, state management, testing. |
| `docs/backend-standard.md` | Backend conventions: architecture, API design, database, auth, testing, deployment. |
| `docs/ui-ux-spec.md` | Visual design system, interaction patterns, responsive behavior, accessibility. |
| `docs/code-review-checklist.md` | Post-implementation review checklist. |
| `docs/verification-checklist.md` | Verification checklist after implementation or before merging. |
| `docs/mcp-setup.md` | Required/optional MCP servers and how to configure them. |
| `opencode.json` | Project-specific opencode settings, permissions, MCP, and instructions. |
| `.opencode/skill/` | Local skills (project-init, project-status). |
| `.opencode/command/` | Slash commands (`/project-init`, `/project-status`). |

## Commands

These commands were discovered by `/project-init` from the manifests under `frontend/` and `backend/`. Run them from the directory shown.

### Frontend (`frontend/`, npm)

- Dev server: `npm run dev`
- Build: `npm run build`
- Preview build: `npm run preview`
- Type check: `npm run check`
- Type check (watch): `npm run check:watch`
- Lint: `npm run lint` (prettier --check . && eslint .)
- Format: `npm run format` (prettier --write .)

### Backend (`backend/`, uv)

- Sync venv: `uv sync`
- Add dep: `uv add <pkg>` / dev: `uv add --dev <pkg>`
- Dev server: `uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Run via fastapi CLI: `uv run fastapi dev --host 0.0.0.0 --port 8000`
- Lint (pending `ruff`): `uv run ruff check .`
- Format (pending `ruff`): `uv run ruff format .`
- Type check (pending `mypy`): `uv run mypy app`
- Test (pending `pytest`): `uv run pytest`
- Migrations (pending `alembic`): `uv run alembic upgrade head` / `uv run alembic revision --autogenerate -m "msg"`

### Local dev (repo root, Docker Compose)

- Bring up the full dev stack: `docker compose --profile dev up` (Postgres + Redis + pgAdmin + backend-dev + frontend-dev, hot reload)
- Production profile: `docker compose --profile prod up`
- Rebuild images: `docker compose up --build`
- Tear down: `docker compose down` (add `-v` to drop data volumes)

## Development environment — how it actually runs (verified 2026-08-03)

The project is developed against a **containerized stack** via Docker (OrbStack on macOS). Agents must assume containers are the running environment — Docker IS the dev flow:

- **Postgres**: container, postgres:16-alpine, host port 5432, creds `app`/`app`, database `app`. Backend config default in `backend/app/core/config.py` points at `postgresql+asyncpg://app:app@localhost:5432/app`.
- **Redis**: container, host port 6379.
- **MailHog**: container (dev profile), SMTP on host port 1025 (no auth), web UI http://localhost:8025. Point a tenant's SMTP config at `host.docker.internal:1025` (NOT 127.0.0.1 - the backend runs in a container and 127.0.0.1 is the container's own loopback), mode None, no username/password to capture outgoing email (invites, resets, notifications) and view it in the UI.
- **pgAdmin**: container, host port 5050 (`admin@zenengr.dev` / `admin`).
- **Backend dev server**: container `zenengr-backend-dev`, port 8000, `./backend/app` volume-mounted for hot reload.
- **Frontend dev server**: container `zenengr-frontend-dev`, port 5173, `./frontend/src` volume-mounted.
- **Tests run on the HOST** (`cd backend && uv run pytest tests/test_<module>.py`) or inside the container (`docker exec zenengr-backend-dev-1 uv run pytest tests/test_<module>.py`) connected to Postgres at `localhost:5432`.
- **Targeted Test Execution Rule:** Only run tests for the **modified module / feature** (e.g. `docker exec zenengr-backend-dev-1 uv run pytest tests/test_statement_invoices_api.py`). Never run the full test suite when verifying a single module change.
- **Targeted Lint / Syntax Rule:** Only check the **modified file(s)**. Do not run full project-wide lint sweeps.
- **Live Dev Server Hot Reload:** The dev server runs in Docker with live volume mounts. Do **NOT** run production builds (`npm run build`) on code updates.
- **Migrations**: `uv run alembic upgrade head` (host) applies to the containerized Postgres.
- Check service state with `docker compose ps` / `docker ps` before blaming environment failures.
- **After adding a backend dependency**, rebuild the backend image — a stale image crashes on import (seen with reportlab, boto3, aiosmtplib): `docker compose --profile dev up -d --build backend-dev` (or `docker exec zenengr-backend-dev-1 uv sync` + restart).
- **After adding a FRONTEND dependency**, install it inside the container (node_modules is not volume-mounted): `docker exec zenengr-frontend-dev-1 npm install`, then RESTART the dev container — `docker restart zenengr-frontend-dev-1` — or reload the page. If the vite dev server was already running before the install, its dependency optimizer has stale state and page modules fail with `Failed to resolve import` (vite:import-analysis) until the server restarts. Rebuilding the image works too: `docker compose --profile dev up -d --build frontend-dev`.

> Lint/type/test commands marked "pending" need the corresponding dev dependency (`ruff`, `mypy`, `pytest`, `alembic`) added via `uv add --dev` before they will work.

## Architecture notes

- **Docs-first workflow:** Feature files drive user stories; stories drive implementation todos. Progress must be updated in that order.
- **Context loading:** Before any implementation task, run `/project-status`, read `Agent.md`, then the specific `docs/features/`, `docs/stories/`, and `docs/todos/` files relevant to the task.
- **Standards separation:** Frontend and backend standards are deliberately separate. Apply the relevant standard based on the task.
- **Review gates:** After implementation, walk the code-review and verification checklists before marking tasks complete in `docs/progress.md`.
- **MCP integration:** Prefer configured MCP servers for external context (file system, git, issue tracker, test runner) over shell commands when available.

## Important conventions

- Keep all project documentation in `docs/`. Do not scatter planning files in the repository root.
- Update `docs/progress.md` after every meaningful change.
- Every implementation task should trace back to a user story and acceptance criteria.
- Do not assume a tech stack. Always run `/project-init` or `docs/prd.md` analysis before writing code for a project using this template.
