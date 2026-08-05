# Progress

## Project status

- **Phase:** Sprint 1 — Admin Auth & Invites
- **Last updated:** 2026-08-05
- **Current focus:** FEAT-012 File Management & Storage shipped: pluggable storage (local + S3-compatible), tenant file gallery with folders, user/team/project visibility scopes, protected project files with client read access, quota, logo/PDF on storage, migration tool. All 137 todos complete.

## What changed recently

| Date | Item | Change |
| ---- | ---- | ------ |
| 2026-08-05 | FEAT-012 File Management & Storage shipped: storage protocol + local + S3(boto3), FileFolder/FileAsset + 2 migrations, folders/upload/list/download/delete APIs, RBAC + quota, client portal file access, logo+PDF via storage, public logo endpoint, backfill/transfer tool, file explorer UI + client files UI | backend/app/storage/*, models/file_folder.py, file_asset.py, services/files.py, api/v1/files.py, client_files.py, public.py, tenant.py, pdf.py, scripts/migrate_storage.py, alembic/versions/c3d4e5f6a7b8_*.py, d4e5f6a7b8c9_*.py, tests/test_storage.py, test_files_api.py, test_client_files_api.py; frontend/src/routes/app/files/*, client/projects/[id], lib/api/files.js, portal.js; docker-compose.yml. |
| 2026-08-05 | FEAT-012 File Management & Storage docs drafted (feature + 5 stories + 15 todos); awaiting approval to implement | docs/features/FEAT-012-file-storage.md, docs/stories/US-048.md, docs/stories/US-049.md, docs/stories/US-050.md, docs/stories/US-051.md, docs/stories/US-052.md, docs/todos/TODO-123.md, docs/todos/TODO-124.md, docs/todos/TODO-125.md, docs/todos/TODO-126.md, docs/todos/TODO-127.md, docs/todos/TODO-128.md, docs/todos/TODO-129.md, docs/todos/TODO-130.md, docs/todos/TODO-131.md, docs/todos/TODO-132.md, docs/todos/TODO-133.md, docs/todos/TODO-134.md, docs/todos/TODO-135.md, docs/todos/TODO-136.md, docs/todos/TODO-137.md, docs/index.md, docs/progress.md. |
| 2026-08-03 | Final: logo upload + render + PDF branding (TODO-011), per-service financial breakdown (TODO-095), voided-invoice correction guidance UI (TODO-083) | backend/app/api/v1/tenant.py, services/pdf.py, financials.py, schemas/projects.py, services/projects.py, main.py, config.py, tests/test_branding_api.py; frontend/src/routes/app/invoices/[id]/+page.svelte, app/+layout.svelte, app/settings/+page.svelte, app/projects/[id]/+page.svelte, lib/api/tenant.js, invoices.js. |
| 2026-08-03 | Void API, invoice PDF (reportlab), client-detail financials, service in-use flag, client-portal data endpoints; frontend invoices + payments + comments UI (TODO-081/082/084/085/091/094/096/097/101/102/105/072/077 done) | backend/app/services/pdf.py, api/v1/invoices.py, client_invoices.py, clients.py, services.py, schemas, tests; frontend src/lib/api/invoices.js, comments.js, src/routes/app/invoices/*, app/projects/[id], components/CommentThread.svelte, StatusBadge.svelte, format.js. |
| 2026-08-03 | FEAT-011 part 2: notification preferences model + endpoints both portals, preference-aware comment dispatch (TODO-108), email change + verification flow (TODO-109/110/116 done) | backend/app/models/notification_preference.py, email_verification_token.py, app/services/notification_preferences.py, account.py, notifications.py, app/api/v1/auth.py, client_auth.py, app/schemas/account.py, alembic/versions/b2c3d4e5f6a7_add_notification_prefs_email.py, tests/test_feat011_api.py, docs/todos/TODO-109/110/116/108.md. |
| 2026-08-03 | FEAT-011 part 1: profile fields + PATCH both portals, change-password, forgot-password (admin + client), password policy setting, activity history model + endpoints (TODO-109 partial, 113/114/115/119 done) | backend/app/models/admin_user.py, client_user.py, client_password_reset_token.py, user_activity.py, app/services/password_policy.py, account.py, settings.py, app/api/v1/auth.py, client_auth.py, users.py, app/schemas/account.py, auth.py, client_auth.py, alembic/versions/a1b2c3d4e5f6_add_profile_password_activity.py, tests/test_feat011_api.py, docs/todos/TODO-109/113/114/115/119.md. |
| 2026-08-03 | FEAT-010 comments backend: Comment model + migration, tenant + client portal comment endpoints, internal/shared visibility (server-side), notification dispatch service (TODO-100/103/104/106/107 done) | backend/app/models/comment.py, app/schemas/comments.py, app/services/comments.py, app/services/notifications.py, app/api/v1/projects.py, app/api/v1/client_projects.py, alembic/versions/f7a8b9c0d1e2_add_comments.py, tests/test_comments_api.py, AGENTS.md, docs/todos/TODO-100/103/104/106/107.md. |
| 2026-08-03 | Dev environment verified: full containerized stack running (OrbStack, 5/5 containers); AGENTS.md updated with how-it-runs docs | AGENTS.md, docs/progress.md. |
| 2026-08-03 | FEAT-009 payments core + TODO-070: Transaction/PaymentAllocation models + migration, record/list transactions, auto+manual allocation, invoice status auto-update, live financial rollups (project/client, batch), clients list wiring, soft-removal endpoint (TODO-089/090/092/093/095/070 done, TODO-042 complete) | backend/app/models/transaction.py, app/schemas/transactions.py, app/services/transactions.py, app/services/financials.py, app/services/clients.py, app/services/projects.py, app/repositories/projects.py, app/api/v1/invoices.py, app/api/v1/projects.py, alembic/versions/e5f6a7b8c9d0_add_transaction_tables.py, tests/test_transactions_api.py, tests/test_projects_api.py, docs/todos/TODO-089/090/092/093/095/070/042.md. |
| 2026-08-03 | FEAT-008 invoicing backend core: Invoice/InvoiceLineItem/InvoiceNumberSequence models + migration, draft create/list/detail/PATCH/DELETE, issue with gapless per-tenant numbering, lock enforcement (TODO-075/076/078/079 done) | backend/app/models/invoice.py, invoice_number_sequence.py, app/schemas/invoices.py, app/services/invoices.py, app/api/v1/invoices.py, alembic/versions/d3e4f5a6b7c8_add_invoice_tables.py, tests/test_invoices_api.py, docs/todos/TODO-075/076/078/079.md. |
| 2026-08-03 | TODO-072 - Project overview API: GET /tenant/projects/{id}/overview (milestone completion pct live; financial + invoice fields placeholder via financials.py seam). 3 tests added, 37 project tests green. Doc reconciliation: TODO-006/009 done, TODO-007 in_progress, US-025 done, US-026-029 in_progress, SPRINT-001 active. | backend/app/api/v1/projects.py, backend/app/services/projects.py, backend/app/schemas/projects.py, backend/app/services/financials.py, backend/tests/test_projects_api.py, docs/todos/TODO-006/007/009/072.md, docs/stories/US-025..029.md, docs/sprints/sprint-001.md, docs/index.md. |
| 2026-07-31 | Project management BE slice (FEAT-007, US-025..US-027) | Project + ProjectService + ProjectMilestone models, migration `c1d2e3f4a5b6`, repos + service + API + 34 tests green. TODO-062/064/065/068 done. Soft-cancel + financial rollups (TODO-070/072) deferred. |
| 2026-07-31 | TODO-063/066/067/069/071/073 — Project management FE slice (FEAT-007) | `lib/api/projects.js` (6 fns); `MilestoneStatusSelector.svelte` (4-state select w/ status colors), `AssigneePicker.svelte`; `/app/projects` routes (list w/ progress bar, new w/ service picker + milestone preview, detail w/ services + grouped milestones + add-service modal, edit); Projects nav item; StatusBadge gained 5 new states (draft/on_hold/completed/in_progress/blocked). `npm run lint` + `npm run check` + `npm run build` pass. |
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
| 2026-07-31 | TODO-062/064/065/068 — Project management BE slice (FEAT-007) | Project + ProjectService + ProjectMilestone models, enum extensions (ProjectStatus, ProjectServiceStatus), migration `c1d2e3f4a5b6`, repository + business service + REST API (POST/GET/PATCH projects, POST services, PATCH milestones), 34 tests green in `tests/test_projects_api.py`. ruff + mypy clean. |
| 2026-07-31 | TODO-063/066/067/069/071/073 — Project management FE slice (FEAT-007) | `lib/api/projects.js` (6 fns); `MilestoneStatusSelector.svelte` (4-state select w/ status colors), `AssigneePicker.svelte`; `/app/projects` routes (list w/ progress bar, new w/ service picker + milestone preview, detail w/ services + grouped milestones + add-service modal, edit); Projects nav item; StatusBadge gained 5 new states (draft/on_hold/completed/in_progress/blocked). `npm run lint` + `npm run check` + `npm run build` pass. |
| 2026-07-31 | TODO-057 + TODO-058 — Service catalog CRUD UI + step ordering (FEAT-006 FE slice) | `frontend/src/lib/api/services.js` (5 fns); `frontend/src/lib/components/MilestoneStepEditor.svelte` (reusable ordered step editor with up/down reorder + add/remove); `/app/services` routes (list + new + detail + edit); Services nav item. `npm run lint` + `npm run check` + `npm run build` all pass. |
| 2026-07-31 | TODO-056 — Service + MilestoneStepTemplate models + migration (FEAT-006 BE slice) | `app/models/service.py`, `app/models/milestone_step_template.py`, `MilestoneStatus` enum, services relationship on Tenant; alembic `b1c2d3e4f5a6`; repository + schemas + business service + API + 18 tests in `tests/test_services_api.py`. |
| 2026-07-31 | TODO-044/045/048/050 — Client UI batch (FEAT-005) | New: `frontend/src/lib/api/clients.js` (9 fns); `frontend/src/routes/app/clients/{+layout,+page}.{js,svelte}` (list + filter form + EmptyState); `frontend/src/routes/app/clients/new/+page.svelte` (create form with chip-tag input); `frontend/src/routes/app/clients/[id]/{+page,edit/+page}.{js,svelte}` (detail w/ profile + financials + contacts + notes + activity timeline, edit form, archive/unarchive flow); `Clients` nav item. `npm run lint` + `npm run check` + `npm run build` pass. |
| 2026-07-31 | TODO-019 + TODO-022 — SA tenant settings panel + plan default flags UI | `frontend/src/lib/api/admin.js` 4 new fns (getTenantSettings, updateTenantSetting, listPlanFlagDefaults, setPlanFlagDefault); SA settings table in `admin/tenants/[id]/+page.svelte`; plan-flags modal in `admin/plans/+page.svelte` (bits-ui Dialog, lazy-loaded). `npm run lint` + `npm run check` pass. |
| 2026-07-31 | TODO-014/018/021/024/041 — tenant plan view, settings, flags, audit UI (stale status) | UI already implemented in earlier sessions but docs flagged as in_progress. Status synced to done. |
| 2026-07-31 | TODO-012 — Plan CRUD API | `app/api/v1/admin.py` POST/GET/list/GET/PATCH/DELETE /api/v1/admin/plans; create/list/get/update/delete in `app/services/plans.py` + `app/repositories/plans.py`; audit on plan.created/updated/deleted. 7 tests in `tests/test_admin_api.py::TestPlansCRUD` green (auth isolation, CRUD, dup-name 409, delete-with-tenants 409). |
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
| 2026-07-27 | Tenant config batch: profile, settings, flags, limits, audits | Profile PATCH greenlet fix, deprecation cleanup, require_feature_flag dependency tests, doc sync. 238 tests green. TODO-010/013/023 done. UI for TODO-014/018/019/021/022/024/041 shipped in later batches. |

## In progress

| Date started | Item / task | Blockers | Notes |
| ------------ | ------------ | -------- | ----- |
| 2026-07-25 | FEAT-001 — Verify `docker compose up` | None (daemon verified up 2026-08-03; 5/5 containers healthy) | Compose stack verified running 2026-08-03: postgres/redis/pgadmin/backend-dev/frontend-dev all Up. Full `docker compose up` (prod profile) verification still pending. |

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

All 137 todos complete (Sprint 1 + FEAT-012 File Management & Storage shipped; 528 backend tests green, frontend clean).

1. Stakeholder walkthrough + demo.
2. Phase 2 candidates: file versioning, virus scanning, thumbnails, client uploads, public share links, S3 lifecycle policies; cloud migration path ready (storage backend switch + transfer tool).
