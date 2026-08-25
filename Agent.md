# Agent.md

Root instructions for opencode operating on any project bootstrapped with this agentic development scaffold.

## On every task start

Load context in this order:

1. Run `/project-status` to get the current state without reading every file.
2. Read `docs/index.md` and `docs/progress.md`.
3. Read `docs/frontend-standard.md` (if working on frontend code)
4. Read `docs/backend-standard.md` (if working on backend code)
5. Read `docs/ui-ux-spec.md` (if working on UI or UX-related changes)
6. Read the specific `docs/features/`, `docs/stories/`, and `docs/todos/` files relevant to the current task.

## Requirement-driven workflow

When the user shares a new requirement, feature request, or change:

1. **Update `docs/features/` and `docs/index.md`**
   - Create or edit a feature file under `docs/features/` (e.g., `docs/features/FEAT-001.md`) with goal, scope, and acceptance criteria.
   - Use `/project-init` if this is the first requirement and the tech stack is unknown.

2. **Update `docs/stories/`**
   - Derive user stories from the feature file.
   - Create one file per story (e.g., `docs/stories/US-001.md`) with stable ID, feature link, and acceptance criteria.

3. **Update `docs/todos/`**
   - Break stories into implementation tasks as individual files (e.g., `docs/todos/TODO-001.md`).
   - Include story ID, feature ID, priority, dependencies, blocks, and acceptance check.

4. **Update `docs/ui-ux-spec.md`** (if frontend/UI impact)
   - Add wireframes, flows, components, states, accessibility notes.

5. **Confirm with the user**
   - Stop and present the updated docs for approval before writing production code.
   - Do not skip this unless the user explicitly opts out.

6. **Implement**
   - Pick the next available todo item.
   - Follow `docs/frontend-standard.md` or `docs/backend-standard.md`.

7. **Post-implementation review**
   - Walk through `docs/code-review-checklist.md` and `docs/verification-checklist.md`.
   - Fix findings before updating progress.

8. **Update `docs/progress.md`**
   - Mark completed tasks and add notes.

## Skills / commands to use

| Situation | Skill / command |
| --------- | --------------- |
| Initial project setup or tech-stack discovery | `/project-init` |
| Current project status and next-task context | `/project-status` |
| Code review after implementation | Use `docs/code-review-checklist.md` |
| Verify behavior end-to-end before marking complete | Use `docs/verification-checklist.md` |

## Development environment — Dockerized mode

The project runs in a **containerized stack** via Docker Compose (`docker compose --profile dev up`):
- **Backend & Frontend dev servers** run inside containers (`zenengr-backend-dev`, `zenengr-frontend-dev`) with volume-mounted source code for live hot reload. **Do NOT run full production builds (`npm run build`)** — the live dev container handles hot-reloading.
- **Postgres, Redis, MailHog, pgAdmin** run as containers.
- **Targeted Test Execution:** Only run tests for the **modified module / feature** (e.g. `docker exec zenengr-backend-dev-1 uv run pytest tests/test_specific_module.py`). Do not execute the entire test suite.
- **Targeted Lint & Syntax Checks:** Only check the **modified file(s)** (e.g. `docker exec zenengr-backend-dev-1 uv run ruff check path/to/file.py` or eslint on the specific file). Do not run full project-wide lint sweeps.

## MCP configuration

- Read `opencode.json` and `docs/mcp-setup.md` to see which MCP servers are configured.
- If the project needs git, database, browser, test-runner, or issue-tracker access and no MCP is configured, suggest entries to add.
- Prefer MCP tools over raw shell commands when both are available.

## Standards enforcement

- All frontend code must follow `docs/frontend-standard.md`.
- All backend code must follow `docs/backend-standard.md`.
- UI changes must reference `docs/ui-ux-spec.md`.
- Any deviation must be approved by the user and documented in `docs/progress.md`.
