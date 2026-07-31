# Project Index

Multi-tenant service, project & billing management platform — MVP.
Tech stack: SvelteKit (frontend/), FastAPI + Postgres (backend/), docker-compose.

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
| Features | 12 | approved: 11, proposed: 1 |
| User stories | 47 | done: 7, proposed: 40 |
| Todos | 122 | done: 43, in_progress: 1, proposed: 78 |
| Decisions | 3 | accepted: 3 |

## Active sprint

| Sprint | Status | Focus |
| ------ | ------ | ----- |
| — | — | Backlog ready — awaiting stakeholder approval before implementation sprint 1 (foundations) |

## Items

### Infrastructure Features

| ID | Title | Status | Priority |
| -- | ----- | ------ | -------- |
| [FEAT-000](features/FEAT-000-local-dev-environment.md) | Local development environment | proposed | high |

### Product Features

| ID | Title | Status | Priority |
| -- | ----- | ------ | -------- |
| [FEAT-001](features/FEAT-001-tenant-management.md) | Tenant Management | approved | P0 |
| [FEAT-002](features/FEAT-002-subscription-settings.md) | Subscription & Settings | approved | P0 |
| [FEAT-003](features/FEAT-003-feature-flags.md) | Feature Flags | approved | P0 |
| [FEAT-004](features/FEAT-004-user-access.md) | User & Access Management | approved | P0 |
| [FEAT-005](features/FEAT-005-client-management.md) | Client Management | approved | P0 |
| [FEAT-006](features/FEAT-006-service-catalog.md) | Service Catalog & Milestones | approved | P0 |
| [FEAT-007](features/FEAT-007-project-management.md) | Project Management | approved | P0 |
| [FEAT-008](features/FEAT-008-invoicing.md) | Invoicing | approved | P0 |
| [FEAT-009](features/FEAT-009-payments.md) | Payments & Financial Tracking | approved | P0 |
| [FEAT-010](features/FEAT-010-comments.md) | Comments / Communication | approved | P0 |
| [FEAT-011](features/FEAT-011-profile-self-service.md) | Profile Management (Self-Service) | approved | P0 |

### Stories

| ID | Title | Feature | Status |
| -- | ----- | ------- | ------ |
| [US-001](stories/US-001.md) | Frontend Docker image | FEAT-000 (infra) | proposed |
| [US-002](stories/US-002.md) | Backend Docker image | FEAT-000 (infra) | proposed |
| [US-003](stories/US-003.md) | Compose stack with all services | FEAT-000 (infra) | proposed |
| [US-004](stories/US-004.md) | Super Admin provisions a tenant | FEAT-001 | proposed |
| [US-005](stories/US-005.md) | Super Admin manages tenant lifecycle | FEAT-001 | proposed |
| [US-006](stories/US-006.md) | Tenant Admin edits own tenant profile | FEAT-001 | proposed |
| [US-007](stories/US-007.md) | Super Admin manages subscription plans | FEAT-002 | proposed |
| [US-008](stories/US-008.md) | Super Admin manages tenant subscription | FEAT-002 | proposed |
| [US-009](stories/US-009.md) | Tenant Admin edits permitted settings | FEAT-002 | proposed |
| [US-010](stories/US-010.md) | Super Admin manages per-tenant feature flags | FEAT-003 | proposed |
| [US-011](stories/US-011.md) | Application enforces feature flags at runtime | FEAT-003 | proposed |
| [US-012](stories/US-012.md) | Tenant Admin invites staff user | FEAT-004 | done |
| [US-013](stories/US-013.md) | Tenant Admin edits/deactivates staff user | FEAT-004 | proposed |
| [US-014](stories/US-014.md) | Tenant Admin triggers password reset | FEAT-004 | proposed |
| [US-015](stories/US-015.md) | RBAC permission matrix enforced server-side | FEAT-004 | proposed |
| [US-016](stories/US-016.md) | Tenant Admin invites/deactivates Client User | FEAT-004 | proposed |
| [US-017](stories/US-017.md) | Audit trail records sensitive actions | FEAT-004 | proposed |
| [US-018](stories/US-018.md) | Staff create/edit/view Clients | FEAT-005 | done |
| [US-019](stories/US-019.md) | Client list with rollups, search, filter | FEAT-005 | done |
| [US-020](stories/US-020.md) | Client activity timeline | FEAT-005 | done |
| [US-021](stories/US-021.md) | Staff archive a Client | FEAT-005 | done |
| [US-022](stories/US-022.md) | Client User edits limited profile fields | FEAT-005 | done |
| [US-023](stories/US-023.md) | Staff manage Service catalog | FEAT-006 | proposed |
| [US-024](stories/US-024.md) | Template edits never mutate project milestones | FEAT-006 | proposed |
| [US-025](stories/US-025.md) | Staff create Project bundling services | FEAT-007 | proposed |
| [US-026](stories/US-026.md) | Staff update milestone status | FEAT-007 | proposed |
| [US-027](stories/US-027.md) | Staff add Service to active Project | FEAT-007 | proposed |
| [US-028](stories/US-028.md) | Cancel invoiced Project Service | FEAT-007 | proposed |
| [US-029](stories/US-029.md) | Project overview with progress + financials | FEAT-007 | proposed |
| [US-030](stories/US-030.md) | Staff create Draft invoice | FEAT-008 | proposed |
| [US-031](stories/US-031.md) | Staff edit Draft then Issue invoice | FEAT-008 | proposed |
| [US-032](stories/US-032.md) | Staff void issued invoice | FEAT-008 | proposed |
| [US-033](stories/US-033.md) | Invoice exported as PDF | FEAT-008 | proposed |
| [US-034](stories/US-034.md) | Client User views own invoices | FEAT-008 | proposed |
| [US-035](stories/US-035.md) | Staff record payment; invoice auto-updates | FEAT-009 | proposed |
| [US-036](stories/US-036.md) | Payment allocation across line items | FEAT-009 | proposed |
| [US-037](stories/US-037.md) | Financial rollups computed from invoices | FEAT-009 | proposed |
| [US-038](stories/US-038.md) | Client User views payment history | FEAT-009 | proposed |
| [US-039](stories/US-039.md) | Post/view project comment thread | FEAT-010 | proposed |
| [US-040](stories/US-040.md) | Internal-only vs shared comment visibility | FEAT-010 | proposed |
| [US-041](stories/US-041.md) | Email notification on new comment | FEAT-010 | proposed |
| [US-042](stories/US-042.md) | User edits own profile | FEAT-011 | proposed |
| [US-043](stories/US-043.md) | User changes password; forgot-password flow | FEAT-011 | proposed |
| [US-044](stories/US-044.md) | User manages notification preferences | FEAT-011 | proposed |
| [US-045](stories/US-045.md) | User views account security history | FEAT-011 | proposed |
| [US-046](stories/US-046.md) | Backend application skeleton and tooling | FEAT-000 (infra) | done |
| [US-047](stories/US-047.md) | Admin realm authentication (JWT login, password hashing, /me) | FEAT-004 | proposed |

### Todos

#### FEAT-000 — Local Development Environment

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-001](todos/TODO-001.md) | Author frontend Dockerfile + .dockerignore | US-001 | done |
| [TODO-002](todos/TODO-002.md) | Author backend Dockerfile + .dockerignore + uvicorn entrypoint | US-002 | done |
| [TODO-003](todos/TODO-003.md) | Author docker-compose.yml + .env.example + healthchecks | US-003 | done |
| [TODO-121](todos/TODO-121.md) | Backend app skeleton, settings, DB session, alembic, tooling | US-046 | done |

#### FEAT-001 — Tenant Management

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-004](todos/TODO-004.md) | Create Tenant model + migration | US-004 | done |
| [TODO-005](todos/TODO-005.md) | Super Admin tenant creation API + UI | US-004 | proposed |
| [TODO-006](todos/TODO-006.md) | Slug validation and uniqueness logic | US-004 | done |
| [TODO-007](todos/TODO-007.md) | Tenant list view | US-005 | proposed |
| [TODO-008](todos/TODO-008.md) | Tenant edit, suspend, deactivate API + UI | US-005 | proposed |
| [TODO-009](todos/TODO-009.md) | Login gate for suspended/deactivated tenants | US-005 | done |
| [TODO-010](todos/TODO-010.md) | Tenant profile self-service page | US-006 | done |
| [TODO-011](todos/TODO-011.md) | Logo and branding field support | US-006 | proposed |

#### FEAT-002 — Subscription & Settings

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-012](todos/TODO-012.md) | Subscription Plan model + CRUD | US-007 | done |
| [TODO-013](todos/TODO-013.md) | Limit enforcement middleware/service | US-007 | done |
| [TODO-014](todos/TODO-014.md) | Tenant plan view page | US-007 | done |
| [TODO-015](todos/TODO-015.md) | Tenant subscription view/edit in Super Admin panel | US-008 | proposed |
| [TODO-016](todos/TODO-016.md) | Subscription status model | US-008 | done |
| [TODO-017](todos/TODO-017.md) | Tenant settings model + permission matrix | US-009 | done |
| [TODO-018](todos/TODO-018.md) | Settings UI for Tenant Admin (editable + view-only) | US-009 | done |
| [TODO-019](todos/TODO-019.md) | Settings UI for Super Admin | US-009 | done |

#### FEAT-003 — Feature Flags

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-020](todos/TODO-020.md) | Feature flag model (key-value per tenant, plan defaults) | US-010 | done |
| [TODO-021](todos/TODO-021.md) | Super Admin flag management UI | US-010 | done |
| [TODO-022](todos/TODO-022.md) | Plan default flag configuration | US-010 | done |
| [TODO-023](todos/TODO-023.md) | Runtime flag check middleware | US-011 | done |
| [TODO-024](todos/TODO-024.md) | Tenant feature status read-only view | US-011 | done |
| [TODO-025](todos/TODO-025.md) | Disabled feature request prompt component | US-011 | proposed |

#### FEAT-004 — User & Access Management

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-026](todos/TODO-026.md) | Invite model + email service | US-012 | done |
| [TODO-027](todos/TODO-027.md) | Registration flow for invited users | US-012 | done |
| [TODO-028](todos/TODO-028.md) | Invite expiry enforcement | US-012 | done |
| [TODO-029](todos/TODO-029.md) | Role edit API + UI | US-013 | done |
| [TODO-030](todos/TODO-030.md) | Deactivate/reactivate API + UI | US-013 | done |
| [TODO-031](todos/TODO-031.md) | Last-admin guard logic | US-013 | done |
| [TODO-032](todos/TODO-032.md) | Admin-triggered password reset API | US-014 | done |
| [TODO-033](todos/TODO-033.md) | Reset email with distinct template | US-014 | done |
| [TODO-034](todos/TODO-034.md) | Role-based permission service | US-015 | done |
| [TODO-035](todos/TODO-035.md) | Endpoint authorization decorators/middleware | US-015 | done |
| [TODO-036](todos/TODO-036.md) | Permission matrix test coverage | US-015 | done |
| [TODO-037](todos/TODO-037.md) | Client User invite flow | US-016 | proposed |
| [TODO-038](todos/TODO-038.md) | Client Portal authentication realm | US-016 | proposed |
| [TODO-039](todos/TODO-039.md) | Client User deactivation | US-016 | proposed |
| [TODO-040](todos/TODO-040.md) | Audit log model + service | US-017 | done |
| [TODO-041](todos/TODO-041.md) | Audit log viewer for Tenant Admin | US-017 | done |
| [TODO-042](todos/TODO-042.md) | Instrument sensitive actions with audit logging | US-017 | in_progress |
| [TODO-122](todos/TODO-122.md) | AdminUser model + JWT auth endpoints (login, me) | US-047 | done |

#### FEAT-005 — Client Management

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-043](todos/TODO-043.md) | Client model + CRUD API | US-018 | done |
| [TODO-044](todos/TODO-044.md) | Client create/edit UI | US-018 | done |
| [TODO-045](todos/TODO-045.md) | Client detail view with contacts | US-018 | done |
| [TODO-046](todos/TODO-046.md) | Client list API with rollups | US-019 | done |
| [TODO-047](todos/TODO-047.md) | Search/filter implementation | US-019 | done |
| [TODO-048](todos/TODO-048.md) | Notes and tags UI | US-019 | done |
| [TODO-049](todos/TODO-049.md) | Activity event model + logging service | US-020 | done |
| [TODO-050](todos/TODO-050.md) | Client activity timeline UI component | US-020 | done |
| [TODO-051](todos/TODO-051.md) | Archive/unarchive API | US-021 | done |
| [TODO-052](todos/TODO-052.md) | Portal access gate for archived clients | US-021 | done |
| [TODO-053](todos/TODO-053.md) | Archived client filter in list views | US-021 | done |
| [TODO-054](todos/TODO-054.md) | Client Portal client profile edit (limited fields) | US-022 | done |
| [TODO-055](todos/TODO-055.md) | Field-level permission enforcement | US-022 | done |

#### FEAT-006 — Service Catalog & Milestones

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-056](todos/TODO-056.md) | Service model + milestone step template model | US-023 | done |
| [TODO-057](todos/TODO-057.md) | Service catalog CRUD API + UI | US-023 | done |
| [TODO-058](todos/TODO-058.md) | Milestone step ordering UI | US-023 | done |
| [TODO-059](todos/TODO-059.md) | Template snapshot logic on project attachment | US-024 | proposed |
| [TODO-060](todos/TODO-060.md) | Template edit warning UI | US-024 | proposed |
| [TODO-061](todos/TODO-061.md) | Instance vs template separation test | US-024 | proposed |

#### FEAT-007 — Project Management

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-062](todos/TODO-062.md) | Project model + create API | US-025 | done |
| [TODO-063](todos/TODO-063.md) | Service selection UI at project creation | US-025 | proposed |
| [TODO-064](todos/TODO-064.md) | Milestone instantiation logic | US-025 | done |
| [TODO-065](todos/TODO-065.md) | Milestone update API | US-026 | done |
| [TODO-066](todos/TODO-066.md) | Milestone status UI with 4-state selector | US-026 | proposed |
| [TODO-067](todos/TODO-067.md) | Assignee picker component | US-026 | proposed |
| [TODO-068](todos/TODO-068.md) | Add service to project API | US-027 | done |
| [TODO-069](todos/TODO-069.md) | Scope growth UI flow | US-027 | proposed |
| [TODO-070](todos/TODO-070.md) | Soft removal logic for invoiced services | US-028 | proposed |
| [TODO-071](todos/TODO-071.md) | Cancelled service indicator in project view | US-028 | proposed |
| [TODO-072](todos/TODO-072.md) | Project overview API (aggregate progress + financial summary) | US-029 | proposed |
| [TODO-073](todos/TODO-073.md) | Project overview UI (Admin Portal) | US-029 | proposed |
| [TODO-074](todos/TODO-074.md) | Client Portal project overview | US-029 | proposed |

#### FEAT-008 — Invoicing

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-075](todos/TODO-075.md) | Invoice model with line items | US-030 | proposed |
| [TODO-076](todos/TODO-076.md) | Draft invoice create API | US-030 | proposed |
| [TODO-077](todos/TODO-077.md) | Draft invoice editor UI | US-030 | proposed |
| [TODO-078](todos/TODO-078.md) | Issue invoice API (number assignment + field lock) | US-031 | proposed |
| [TODO-079](todos/TODO-079.md) | Invoice number generator (tenant-scoped sequential) | US-031 | proposed |
| [TODO-080](todos/TODO-080.md) | Lock enforcement on Issued invoices | US-031 | proposed |
| [TODO-081](todos/TODO-081.md) | Void invoice API + status update | US-032 | proposed |
| [TODO-082](todos/TODO-082.md) | Voided invoice display state | US-032 | proposed |
| [TODO-083](todos/TODO-083.md) | Correction workflow guidance in UI | US-032 | proposed |
| [TODO-084](todos/TODO-084.md) | PDF generation service | US-033 | proposed |
| [TODO-085](todos/TODO-085.md) | PDF template with invoice layout | US-033 | proposed |
| [TODO-086](todos/TODO-086.md) | Download button in invoice views | US-033 | proposed |
| [TODO-087](todos/TODO-087.md) | Client Portal invoice list view | US-034 | proposed |
| [TODO-088](todos/TODO-088.md) | Client Portal invoice detail view | US-034 | proposed |

#### FEAT-009 — Payments & Financial Tracking

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-089](todos/TODO-089.md) | Transaction model + record API | US-035 | proposed |
| [TODO-090](todos/TODO-090.md) | Invoice status auto-update logic | US-035 | proposed |
| [TODO-091](todos/TODO-091.md) | Payment recording UI | US-035 | proposed |
| [TODO-092](todos/TODO-092.md) | Payment allocation model | US-036 | proposed |
| [TODO-093](todos/TODO-093.md) | Auto-allocation algorithm (proportional/FIFO) | US-036 | proposed |
| [TODO-094](todos/TODO-094.md) | Allocation override UI | US-036 | proposed |
| [TODO-095](todos/TODO-095.md) | Financial rollup computation service | US-037 | proposed |
| [TODO-096](todos/TODO-096.md) | Project financial summary component | US-037 | proposed |
| [TODO-097](todos/TODO-097.md) | Client financial summary component | US-037 | proposed |
| [TODO-098](todos/TODO-098.md) | Client Portal payment history view | US-038 | proposed |
| [TODO-099](todos/TODO-099.md) | Client Portal outstanding balance display | US-038 | proposed |

#### FEAT-010 — Comments / Communication

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-100](todos/TODO-100.md) | Comment model + post API | US-039 | proposed |
| [TODO-101](todos/TODO-101.md) | Comment thread UI component | US-039 | proposed |
| [TODO-102](todos/TODO-102.md) | Comment thread in Admin Portal | US-039 | proposed |
| [TODO-103](todos/TODO-103.md) | Internal/shared comment flag on post | US-040 | proposed |
| [TODO-104](todos/TODO-104.md) | Visibility filtering in thread queries | US-040 | proposed |
| [TODO-105](todos/TODO-105.md) | Internal comment visual indicator | US-040 | proposed |
| [TODO-106](todos/TODO-106.md) | Comment notification email template | US-041 | proposed |
| [TODO-107](todos/TODO-107.md) | Notification dispatch service | US-041 | proposed |
| [TODO-108](todos/TODO-108.md) | Preference-aware notification filtering | US-041 | proposed |

#### FEAT-011 — Profile Management (Self-Service)

| ID | Title | Story | Status |
| -- | ----- | ----- | ------ |
| [TODO-109](todos/TODO-109.md) | Profile edit API (both portals) | US-042 | proposed |
| [TODO-110](todos/TODO-110.md) | Email change with re-verification | US-042 | proposed |
| [TODO-111](todos/TODO-111.md) | Profile UI (Admin Portal) | US-042 | proposed |
| [TODO-112](todos/TODO-112.md) | Profile UI (Client Portal) | US-042 | proposed |
| [TODO-113](todos/TODO-113.md) | Password change API | US-043 | proposed |
| [TODO-114](todos/TODO-114.md) | Forgot-password flow | US-043 | proposed |
| [TODO-115](todos/TODO-115.md) | Password policy validation | US-043 | proposed |
| [TODO-116](todos/TODO-116.md) | Notification preference model | US-044 | proposed |
| [TODO-117](todos/TODO-117.md) | Notification preference UI | US-044 | proposed |
| [TODO-118](todos/TODO-118.md) | Preference-aware notification dispatch | US-044 | proposed |
| [TODO-119](todos/TODO-119.md) | User activity history model + logging | US-045 | proposed |
| [TODO-120](todos/TODO-120.md) | Activity history UI component | US-045 | proposed |

## Recently updated

| Date | Item | Change |
| ---- | ---- | ------ |
| 2026-07-31 | Project management BE slice complete (FEAT-007 US-025..US-027) | TODO-062/064/065/068 done. Project + ProjectService + ProjectMilestone models, migration `c1d2e3f4a5b6`, repos + service + API, 34 tests green, ruff + mypy clean. Soft-cancel + financial rollups (TODO-070/072) deferred to follow-up. |
| 2026-07-27 | Client management APIs complete (FEAT-005 US-018..US-022) | TODO-043/046/047/049/051/052/053/054/055 done. Full CRUD, list+rollups, search/filter, archive/unarchive, notes, tags, activity timeline, client portal self-service profile edit. 35 tests green, ruff + mypy clean. |
| 2026-07-26 | `docs/todos/TODO-004..TODO-120.md`, `docs/index.md`, `docs/progress.md` | Generated implementation backlog (117 todos) from US-004..US-045; refreshed dashboard and progress. |
| 2026-07-26 | `docs/stories/US-046.md`, `docs/todos/TODO-121.md` | Backend skeleton story + todo (done). |
| 2026-07-26 | `docs/stories/US-047.md`, `docs/todos/TODO-122.md` | Admin auth gap story + todo (proposed). |
| 2026-07-26 | `docs/index.md`, `docs/progress.md` | Updated counts (47 stories, 122 todos, 4 done), sprint 1 started. |
| 2026-07-26 | `docs/index.md`, `docs/features/FEAT-000-local-dev-environment.md`, `docs/stories/US-004..US-045.md`, `docs/decisions/ADR-003.md` | Renumbered infra feature FEAT-001->FEAT-000; created 42 product stories US-004..US-045; recorded 6 MVP scope decisions as ADR-003. |
| 2026-07-26 | `docs/prd.md` | Saved BRD v0.1 as source of truth. |
| 2026-07-26 | `docs/features/FEAT-001..FEAT-011` | Created 11 product feature files from PRD modules. |
| 2026-07-26 | `docs/index.md` | Added product feature table and PRD reference. |
| 2026-07-25 | `docs/stack-discovery.md` | Filled by `/project-init` (SvelteKit + FastAPI detected). |
| 2026-07-25 | `docs/features/FEAT-001.md` | Replaced auth placeholder with Local dev environment feature. |
| 2026-07-25 | `docs/stories/US-001..US-003.md`, `docs/todos/TODO-001..TODO-003.md` | Created for dev-env feature. |

## How to add items

1. **Feature:** Copy `docs/features/FEAT-NNN-*.md`, assign next `FEAT-NNN` ID, update frontmatter.
2. **Story:** Copy `docs/stories/US-NNN.md`, assign next `US-NNN` ID, link to feature via `feature:`.
3. **Todo:** Copy `docs/todos/TODO-NNN.md`, assign next `TODO-NNN` ID, link to story/feature.
4. **Decision:** Copy `docs/decisions/ADR-NNN.md`, assign next `ADR-NNN` ID.

## Next

Backlog ready — 117 implementation todos generated from 42 product stories across 11 features. Awaiting stakeholder approval before implementation. Suggested first sprint: FEAT-001/FEAT-004 foundations (tenant model, dual auth realms, RBAC).
