# Project Index

Auto-generated project dashboard. Run `/project-status` to refresh; edit individual files in
`docs/features/`, `docs/stories/`, `docs/todos/`, and `docs/decisions/`.

## Quick filters

| View | How to find |
| ---- | ----------- |
| Active work | `docs/todos/` with `status: in_progress` |
| Proposed features | `docs/features/` with `status: proposed` |
| Blocked items | `docs/todos/` with `status: blocked` |
| Decisions | `docs/decisions/` |

## Status overview

| Area | Count | Key metric |
| ---- | ----- | ---------- |
| Features | 1 | proposed: 1 |
| User stories | 3 | proposed: 3 |
| Todos | 3 | done: 3 |
| Decisions | 1 | accepted: 1 |

## Active sprint

| Sprint | Status | Focus |
| ------ | ------ | ----- |
| — | — | FEAT-001 Local development environment scaffolding |

## Items

### Features

| ID | Title | Status | Priority |
| -- | ----- | ------ | -------- |
| [FEAT-001](features/FEAT-001.md) | Local development environment | proposed | high |

### Stories

| ID | Title | Feature | Status |
| -- | ----- | ------- | ------ |
| [US-001](stories/US-001.md) | Frontend Docker image | FEAT-001 | proposed |
| [US-002](stories/US-002.md) | Backend Docker image | FEAT-001 | proposed |
| [US-003](stories/US-003.md) | Compose stack with all services | FEAT-001 | proposed |

### Todos

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-001](todos/TODO-001.md) | Author frontend Dockerfile + .dockerignore | US-001 | done |
| [TODO-002](todos/TODO-002.md) | Author backend Dockerfile + .dockerignore + uvicorn entrypoint | US-002 | done |
| [TODO-003](todos/TODO-003.md) | Author docker-compose.yml + .env.example + healthchecks | US-003 | done |

## Recently updated

| Date | Item | Change |
| ---- | ---- | ------ |
| 2026-07-25 | `docs/stack-discovery.md` | Filled by `/project-init` (SvelteKit + FastAPI detected). |
| 2026-07-25 | `docs/features/FEAT-001.md` | Replaced auth placeholder with Local dev environment feature. |
| 2026-07-25 | `docs/stories/US-001..US-003.md`, `docs/todos/TODO-001..TODO-003.md` | Created for dev-env feature. |

## How to add items

1. **Feature:** Copy `docs/features/FEAT-001.md`, assign next `FEAT-NNN` ID, update frontmatter.
2. **Story:** Copy `docs/stories/US-001.md`, assign next `US-NNN` ID, link to feature via `feature:`.
3. **Todo:** Copy `docs/todos/TODO-001.md`, assign next `TODO-NNN` ID, link to story/feature.
4. **Decision:** Copy `docs/decisions/ADR-001.md`, assign next `ADR-NNN` ID.

## Next

FEAT-001 todos done. Verify with `docker compose up` (after starting Docker daemon).
Share the PRD to scope FEAT-002+ (product features).