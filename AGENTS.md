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
- **pgAdmin**: container, host port 5050 (`admin@zenengr.dev` / `admin`).
- **Backend dev server**: container `zenengr-backend-dev`, port 8000, `./backend/app` volume-mounted for hot reload.
- **Frontend dev server**: container `zenengr-frontend-dev`, port 5173, `./frontend/src` volume-mounted.
- **Docker daemon must be running for everything, including tests.** Verify with `docker ps`. If the daemon is down, Postgres is unreachable and tests/backend fail — do not assume the code is broken.
- **Tests run on the HOST** (`cd backend && uv run pytest`) but connect to the **containerized** Postgres at `localhost:5432`. `backend/tests/conftest.py` auto-creates and drops an `app_test` database per session.
- **Backend checks** (`uv run ruff check .`, `uv run mypy app`, `uv run pytest`) run from `backend/` on the host against the container services.
- **Migrations**: `uv run alembic upgrade head` (host) applies to the containerized Postgres.
- Check service state with `docker compose ps` / `docker ps` before blaming environment failures.

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
