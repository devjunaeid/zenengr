# Progress

## Project status

- **Phase:** Sprint 1 — Admin Auth & Invites
- **Last updated:** 2026-07-27
- **Current focus:** Client management APIs (FEAT-005) complete. 35 tests green. UI pending.

## What changed recently

| Date | Item | Change |
| ---- | ---- | ------ |
| 2026-07-27 | Client management APIs (FEAT-005, US-018..US-022) | Full CRUD, list+rollups, search/filter, archive/unarchive, notes, tags, activity timeline, client portal self-service profile edit. 35 tests green. ruff + mypy clean. TODO-043/046/047/049/051/052/053/054/055 done. UI todos in_progress. |
| 2026-07-27 | Client realm (Client/ClientNote/ClientUser/ClientInvite models, migration, tests) | Migration 81cfc015e65d, 276 tests green, ruff + mypy clean. Added drop_all to session fixture for clean test isolation. |
| 2026-07-26 | Backend skeleton (US-046 / TODO-121) | Created full app skeleton, tooling, alembic, tests — all green. |
| 2026-07-26 | Gap docs US-047 / TODO-122 | Admin auth story + todo (proposed) for next sprint. |
| 2026-07-26 | Batch B — 9 core SQLAlchemy models + migration | Plan, Tenant, TenantSubscription, TenantSetting, PlanFeatureDefault, TenantFeatureFlag, AuditLog, AdminUser, Invite — all with enums, FKs, uniques, indexes. Tests: 29/29 green. |
| 2026-07-27 | Admin JWT auth + RBAC (TODO-122/034/035/036) | Password hashing (bcrypt), JWT HS256 service, RBAC matrix per FR-4.2, auth deps (require_permission/require_roles), login + /me endpoints, seed script, 96 tests green. |
| 2026-07-26 | Slug validation util, feature flag resolution service, email abstraction | `app/utils/slug.py`, `app/services/feature_flags.py`, `app/services/email.py`. |
| 2026-07-26 | TODO-004/040/016/017/020 → done; TODO-012/026 → in_progress | Model+ migration done; CRUD APIs pending for Plan and Invite. |
| 2026-07-26 | `docs/index.md`, `docs/progress.md` | Updated counts (47 stories, 122 todos, 4 done); sprint 1 active. |
| 2026-07-26 | `docs/todos/TODO-004..TODO-120.md` | Generated 117 implementation todos from US-004..US-045 stories across 11 features. |
| 2026-07-26 | `docs/index.md`, `docs/progress.md` | Refreshed dashboard with full todo table by feature; updated progress tracker. |
| 2026-07-26 | PRD v0.1 saved | 11 features approved, 42 stories US-004..US-045 created, ADR-003 accepted. |
| 2026-07-26 | ADR-003 | 6 MVP scope decisions recorded. |
| 2026-07-26 | `docs/features/FEAT-001..FEAT-011` | Created 11 product feature files from PRD modules. |
| 2026-07-26 | `docs/stories/US-004..US-045.md` | Created 42 product user stories across all 11 features. |
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
| 2026-07-27 | TODO-043/046/047/049/051/052/053/054/055 — Client management APIs | Full CRUD, list+rollups, search/filter, archive/unarchive, notes, tags, activity timeline, client portal self-service profile edit. 35 tests green. ruff + mypy clean. |
| 2026-07-27 | TODO-037/038/039 — Client data layer + Client Portal auth realm | Client/ClientNote/ClientUser/ClientInvite models, client-realm JWT auth, invite flow, deactivation, realm isolation. 4 new tables, migration `81cfc015e65d`. Ruff + mypy clean. |
| 2026-07-24 | Scaffold template files | `docs/features`, `docs/stories`, `docs/todos`, `docs/decisions`. |
| 2026-07-25 | `/project-init` completed | Stack detected and documented; FEAT-001 created. |
| 2026-07-25 | TODO-001 — Frontend Dockerfile + .dockerignore | `frontend/Dockerfile`, `frontend/.dockerignore`; switched to adapter-node for Docker. |
| 2026-07-25 | TODO-002 — Backend Dockerfile + .dockerignore + entrypoint | `backend/app/main.py`, `backend/Dockerfile`, `backend/.dockerignore`. |
| 2026-07-25 | TODO-003 — docker-compose.yml + .env.example | Repo-root `docker-compose.yml` (5 services), `.env.example`. |
| 2026-07-25 | Dev profile docker-compose | Added `frontend-dev` + `backend-dev` services with `profiles: [dev]`, volume mounts, `--reload` flag, separate Dev Dockerfiles. |
| 2026-07-26 | PRD v0.1 saved, 11 features approved | BRD received from product owner; 11 product feature files created and approved. |
| 2026-07-26 | User stories US-004..US-045 | 42 product stories derived from feature files. |
| 2026-07-26 | ADR-003 accepted | 6 MVP scope decisions recorded (sequential completion, soft-delete strategy, etc.). |
| 2026-07-26 | Backlog TODO-004..TODO-120 | 117 implementation todos generated from US-004..US-045 across all 11 features. |
| 2026-07-26 | TODO-121 — Backend app skeleton | Full skeleton created, tooling configured, all checks green. |
| 2026-07-26 | Gap docs US-047 + TODO-122 | Proposed for admin auth — next sprint item. |
| 2026-07-26 | TODO-012/016/017 — Plan + TenantSubscription + TenantSetting models | Plan limits config, subscription linking, settings with permission levels. |
| 2026-07-26 | TODO-020 — Feature flag models + resolution service | TenantFeatureFlag, PlanFeatureDefault, `is_feature_enabled()` resolution. |
| 2026-07-26 | TODO-004/006 — Tenant model + slug validation | Tenant with slug unique index, `validate_slug()` regex util. |
| 2026-07-26 | TODO-026 — Invite model + email abstraction | Invite with token hash, ConsoleEmailSender protocol. |
| 2026-07-26 | TODO-040 — AuditLog model | Append-only model without updated_at. |
| 2026-07-27 | TODO-026/027/028 — Invite API full flow | invite CRUD (tenant-scoped, admin-only), token lookup, registration, audit, email sending. 119 tests green. |
| 2026-07-27 | TODO-029 — Role edit API | PATCH /tenant/users/{id}/role with last-admin guard, audit. |
| 2026-07-27 | TODO-030 — Deactivate/reactivate API | POST deactivate/reactivate endpoints, login gate, audit. |
| 2026-07-27 | TODO-031 — Last-admin guard | `ensure_not_last_admin()` service, wired into role change + deactivate. |
| 2026-07-27 | TODO-032 — Admin-triggered password reset API | POST /tenant/users/{id}/reset-password + public POST /auth/reset-password consume. |
| 2026-07-27 | TODO-033 — Reset email template | Distinct "Your administrator initiated a password reset" email. |
| 2026-07-27 | TODO-010 — Tenant profile API | Profile GET/PATCH with audit, permission gates. API done. |
| 2026-07-27 | TODO-013 — Limit enforcement service | check_limit + LimitExceededError, wired into invites. |
| 2026-07-27 | TODO-023 — Runtime flag check dependency | require_feature_flag dep with tests for disabled/enabled/flip/SA exemption. |
| 2026-07-27 | Tenant config batch: profile, settings, flags, limits, audits | Profile PATCH greenlet fix, deprecation cleanup, require_feature_flag dependency tests, doc sync. 238 tests green. TODO-010/013/023 done. TODO-014/018/019/021/022/024/041 in_progress (UI pending). |

## In progress

| Date started | Item / task | Blockers | Notes |
| ------------ | ------------ | -------- | ----- |
| 2026-07-25 | FEAT-001 — Verify `docker compose up` | Docker daemon not running on this machine | Builds verified (`npm run build` + adapter-node). Verify full compose after starting Docker. |
| 2026-07-27 | TODO-012 — Plan CRUD API | None | Plan model done; CRUD API pending. |
| 2026-07-27 | TODO-042 — Instrument sensitive actions (partial) | User-admin actions done; invoice/payment hooks in later batches | See TODO-042 for wired vs pending. |
| 2026-07-27 | TODO-014 — Tenant plan view page | API done (GET /tenant/plan + usage). | UI pending. |
| 2026-07-27 | TODO-018 — Settings UI for Tenant Admin | API done (GET/PATCH /tenant/settings). | UI pending. |
| 2026-07-27 | TODO-019 — Settings UI for Super Admin | API done (admin settings endpoints). | UI pending. |
| 2026-07-27 | TODO-021 — Super Admin flag management UI | API done (admin flag CRUD endpoints). | UI pending. |
| 2026-07-27 | TODO-022 — Plan default flag configuration | API done (plan flag CRUD endpoints). | UI pending. |
| 2026-07-27 | TODO-024 — Tenant feature status read-only view | API done (GET /tenant/flags). | UI pending. |
| 2026-07-27 | TODO-041 — Audit log viewer for Tenant Admin | API done (GET /tenant/audit-logs + admin equivalents). | UI pending. |
| 2026-07-27 | TODO-044 — Client create/edit UI | API done (TODO-043). | UI pending (later frontend batch). |
| 2026-07-27 | TODO-045 — Client detail view with contacts | API done (TODO-043). | UI pending (later frontend batch). |
| 2026-07-27 | TODO-048 — Notes and tags UI | API done (notes/tags endpoints). | UI pending (later frontend batch). |
| 2026-07-27 | TODO-050 — Client activity timeline UI | API done (TODO-049). | UI pending (later frontend batch). |

## Blocked

| Item / task | Blocker | Owner |
| ------------ | ------- | ----- |
| FEAT-001+ (product features implementation) | Awaiting stakeholder approval of backlog | User |

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

1. TODO-012 — Plan CRUD API (list, create, update for super_admin).
2. Frontend: build accept-invite page (TODO-037 is separate client-user invite batch).
3. Stakeholder approval gate for remaining backlog.
4. Continue sprint 1: FEAT-004 foundations (Plan CRUD, tenant onboarding).
