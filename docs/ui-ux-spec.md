# UI/UX Specification

> This file holds framework-agnostic defaults. No design system exists yet — refine these tokens
> and add page-by-page notes _before_ frontend implementation of any PRD-driven feature
> (per `Agent.md` workflow).

## Design system

- **Color palette:** TBD — default to Tailwind v4's theme tokens (`--color-*`), overridden via `layout.css`.
  Suggested semantic mappings:
  - `primary`, `primary-foreground` — primary actions
  - `secondary`, `secondary-foreground`
  - `muted`, `muted-foreground` — secondary text
  - `destructive` — errors
  - `border`, `input`, `ring`
- **Typography:** System font stack default (Tailwind). Brand fonts TBD.
  - Sizes use Tailwind text scale; weights 400/500/600/700.
- **Spacing scale:** 4px grid (`gap-1` = 4px) — Tailwind v4 defaults.
- **Corner radius:** default `--radius: 0.5rem`; tight controls `rounded-md` (0.375rem), cards `rounded-lg` (0.5rem).
- **Shadows / elevations:** Tailwind `shadow-sm/md/lg/xl`; elevate modals and dropdowns.

## Component library

- **Library:** bits-ui (headless primitives) + Tailwind-styled wrappers co-located in `src/lib/components/`.
- **Core components to build/adopt:** Button, Input, Label, Field, Card, Modal (Dialog), Toast, Tooltip,
  Dropdown, Select, Tabs, Table, Skeleton/Spinner.
- Pattern: bits-ui primitive inside a thin `.svelte` wrapper that applies Tailwind styles and our tokens; consumers import the wrapper.

## Layout

- **Breakpoints:** Tailwind defaults — `sm: 640`, `md: 768`, `lg: 1024`, `xl: 1280`, `2xl: 1536`.
- **Max content width:** `max-w-7xl` (1280px) for app shells; article-style pages `max-w-3xl` (768px).
- **Navigation pattern:** TBD (likely top nav + sidebar once dashboard feature is defined).

## Interactions

- **Loading states:** Skeletons for data-dense areas; spinners for short actions; `disabled` + `aria-busy` on buttons during submit.
- **Empty states:** Provide headline + helpful copy + primary CTA in list/index views.
- **Error states:** Inline (form fields) + toast (network-level) — never silent.
- **Form validation:** Client hints via HTML + ARIA; server is source of truth; surface `details` per field.
- **Toast / notification:** Centered-top or bottom-right stack; auto-dismiss after ~6s; persist error toasts.

## Accessibility

- **Target WCAG level:** 2.1 AA.
- **Focus management:** Visible focus ring via `:focus-visible` (Tailwind `focus-visible:ring`); trap focus in modals/drawers; restore focus on close.
- **ARIA conventions:** Use bits-ui primitives' built-in ARIA; never override without reason; label all controls.
- **Keyboard navigation:** All interactive elements reachable via Tab; Escape closes overlays; Enter/Space activates.
- **Color contrast:** Text on backgrounds ≥ 4.5:1; large text ≥ 3:1.

## Surfaces overview

Three distinct UI surfaces, each with separate login/auth realm:

| Surface | Auth realm | Users | Tenant data access |
|---|---|---|---|
| Super Admin Console | Platform | Super Admin | None (container-level only) |
| Admin / Ops Portal | Tenant staff | Tenant Admin, Manager, Employee | Own tenant data |
| Client Portal | Client | Client Users | Own client data only |

**Login realms:**
- Admin/Ops Portal and Super Admin Console share auth backend; Super Admin is role-gated, NOT tenant-scoped.
- Client Portal uses separate login URL/page, separate session scope, never shares session with admin realm.

## Screen inventory

### Super Admin Console

| Screen | Purpose | Primary role | Key data / actions | Source FR |
|---|---|---|---|---|
| Tenant List | Browse, search, filter all tenants | Super Admin | Name, slug, plan, status (Trial/Active/Suspended/Cancelled), created date. Actions: create, suspend, deactivate. | FR-1.1 |
| Tenant Detail / Edit | View and edit single tenant profile | Super Admin | Name, slug, contact info, lifecycle status, subscription plan, feature flag list, settings. | FR-1.1, FR-1.2, FR-1.3 |
| Tenant Subscription | Assign plan, view/edit subscription status | Super Admin | Plan selector, billing cycle, renewal date, status. Limit enforcement indicators. | FR-2.1, FR-2.3 |
| Feature Flags per Tenant | Toggle feature flags on/off | Super Admin | Key-value flag list with toggle per tenant. Plan-default vs override indicator. | FR-3.1, FR-3.2, FR-3.3 |
| Plan Management | CRUD subscription plans | Super Admin | Plan name, limit fields (max users/clients/projects/storage), default feature flag map. | FR-2.2 |
| Platform Settings | Global platform config | Super Admin | (MVP minimal -- shared tenant-setting defaults, timezone, currency options.) | FR-2.4 |

**NO tenant operational data** (clients, projects, invoices, comments) anywhere in this UI.

### Admin / Ops Portal

| Screen | Purpose | Primary role(s) | Key data / actions | Source FR |
|---|---|---|---|---|
| Dashboard | Overview of key metrics | Admin, Manager | Active projects count, outstanding invoices, recent activity feed. (MVP: simple stats, not full BI.) | -- |
| Staff Users | Manage tenant staff | Admin | User list: name, email, role, status (active/deactivated). Actions: invite, edit role, deactivate/reactivate, password reset. | FR-4.1, FR-4.9--4.14 |
| Client List | Browse, search, filter clients | Admin, Manager | Name, status, active projects count, total invoiced, outstanding balance. Actions: create, edit, archive. | FR-5.1, FR-5.4, FR-5.7 |
| Client Detail / Edit | View/edit single client | Admin, Manager | Contact info, billing address, tax ID, status toggle. Tabs: Notes (internal-only), Activity History, Client Users. | FR-5.2, FR-5.3, FR-5.5, FR-5.6 |
| Service Catalog | Manage services and milestone templates | Admin, Manager | Service list with price. Create/edit: name, price, ordered milestone steps. Template immutability warning. | FR-6.1--6.3, FR-6.5 |
| Project List | Browse, search, filter projects | Admin, Manager, Employee (assigned) | Name, client, status, owner, progress %, balance due. Actions: create, edit, change status. | FR-7.1, FR-7.2 |
| Project Detail | Full project overview | Admin, Manager, Employee (assigned) | Tabs: Overview (progress %, financial summary, linked invoices), Services (with milestone statuses), Invoice History, Comments. Add service action. | FR-7.3--7.6 |
| Milestone Status Update | Update individual milestone status | Admin, Manager, Employee (assigned) | Status selector (Pending/In Progress/Completed/Blocked), completion date, notes. | FR-6.4, FR-6.6 |
| Invoice List | Browse project invoices | Admin, Manager | Invoice number, project, client, total, status badge, due date, balance due. | FR-8.1--8.3 |
| Invoice Detail / Edit (Draft) | Create and edit draft invoices | Admin, Manager | Line items (service selection), subtotal, tax, total. Save draft, issue action. | FR-8.1, FR-8.2, FR-8.4 |
| Invoice Detail (Issued) | View issued invoice (locked) | Admin, Manager | Read-only financial fields. Actions: void, record payment, view PDF. Status badge. | FR-8.4, FR-8.7 |
| Record Payment | Record transaction against invoice | Admin, Manager | Amount, date, method, reference note. Line-item allocation table with auto-proposed and manual override. | FR-9.1--9.3 |
| Comments Thread | Project-level communication | Admin, Manager, Employee (assigned) | Message list with author/timestamp. Internal-only toggle per comment. Shared vs internal badge. | FR-10.1--10.4 |
| Tenant Settings | View/edit tenant operational config | Admin (edit), Manager (view) | Currency, invoice numbering format, timezone, date format, email sender identity. Permission-cued visibility. | FR-2.4, FR-2.5 |
| Activity Log | Audit trail of sensitive actions | Admin | Chronological list: who did what, when. Filterable. | FR-4.13 |
| Profile (Admin) | Self-service profile | All admin roles | Name, avatar, email, phone, timezone, language, password change, notification prefs. | FR-11.1--11.6 |

### Client Portal

| Screen | Purpose | Primary role | Key data / actions | Source FR |
|---|---|---|---|---|
| Login | Separate auth entry point | Client User | Email + password. Branded per-tenant logo/name. | FR-4.6, FR-1.5 |
| Dashboard / My Projects | Project list for own client | Client User | Project name, status, overall progress %, linked invoice count, balance due. | FR-7.5, FR-9.5 |
| Project Detail | View project progress and financials | Client User | Milestone list with status read-only, financial summary (invoiced/paid/due). No edit actions. | FR-7.5, FR-6.6 |
| Invoices | All invoices for own projects | Client User | Invoice number, project, total, status badge, balance due, paid amount, PDF download. | FR-8.6, FR-8.7 |
| Comments | Shared comment thread per project | Client User | Read messages (shared only), post new messages. No visibility of internal-only comments. | FR-10.1, FR-10.3 |
| Profile (Client) | Self-service profile | Client User | Name, avatar, email, phone, password change, notification prefs. Limited client contact edit. | FR-5.9, FR-11.1--11.6 |
| Client Profile (read/limited-edit) | View/edit own company contact fields | Client User | Contact details (phone, email). NOT billing-sensitive fields (tax ID, billing address). | FR-5.9 |

## Key flows

### Flow 1: Super Admin provisions a tenant

1. Super Admin opens Tenant List -> clicks "Create Tenant".
2. Form: tenant name, slug, contact info. Optional: initial plan assignment.
3. Submit -> tenant created with `Trial` or `Active` status.
4. Super Admin navigates to tenant's Subscription tab -> assigns or changes plan.
5. Super Admin navigates to Feature Flags tab -> toggles flags as needed for this tenant.
6. Super Admin navigates to tenant detail -> can optionally trigger invite email to tenant Admin.
7. Tenant Admin receives invite email -> clicks link -> sets password -> logs into Admin/Ops Portal -> sees empty tenant-ready workspace (no clients, no projects).

### Flow 2: Tenant Admin invites staff user

1. Tenant Admin opens Staff Users screen -> clicks "Invite User".
2. Form: email, role (Admin/Manager/Employee), optional message.
3. Submit -> system sends invite email with expiry.
4. Recipient clicks invite link -> set-password form -> role pre-assigned.
5. User logs into Admin/Ops Portal with correct permission scope.
6. If invite expires, Tenant Admin sees expired status and can resend.

### Flow 3: Create project with services -> milestones instantiated

1. Tenant Admin/Manager opens Project List -> clicks "Create Project".
2. Form: name, client (select from active clients), start date, owner, status.
3. Service selection: pick one or more services from catalog. Each shows milestone count.
4. Submit -> project created. For each selected service, milestone template instantiated: each template step becomes a `Pending` project milestone with planned date derived.
5. Project Detail screen now shows Services tab with milestone rows. Tenant staff can update milestone status individually.
6. Client sees new project appear on Client Portal with `Pending` milestones (read-only).

### Flow 4: Draft invoice -> edit -> Issue -> record payment (with line-item allocation)

1. Tenant Admin/Manager opens Project Detail -> Invoice History tab -> clicks "Create Invoice".
2. Select line items: check which Project Services to include. Each line shows price. Optional custom line item.
3. System pre-fills issue date (today), due date (default from settings), subtotal, optional tax, total.
4. Save as Draft -> invoice editable.
5. Later, open Draft invoice -> edit line items, amounts, dates as needed.
6. Click "Issue" -> confirmation dialog (warning: irreversibly locks financial fields).
7. On confirm -> invoice status changes to `Issued`/`Sent`. Invoice number assigned (tenant-scoped sequential). Core fields locked.
8. Project Overview financial summary updates to include new invoice.
9. Client Portal shows new invoice with `Issued` badge and balance due.
10. Later, tenant staff opens issued invoice -> clicks "Record Payment".
11. Payment form: amount, date, method, reference note.
12. If invoice has multiple line items, system shows allocation table:
    - Proposed auto-allocation (proportional by amount).
    - Tenant staff can manually override per-line-item paid amount.
    - Validation ensures sum of allocated amounts = payment amount.
13. Submit -> Transaction recorded. Invoice status auto-updates:
    - If payment amount < invoice total -> `Partially Paid`.
    - If payment >= total -> `Paid`.
14. Project financial summary refreshes.
15. Client Portal shows updated invoice status and payment history entry.

### Flow 5: Client User login -> view project -> view invoice -> post comment

1. Client User navigates to Client Portal login URL (not Admin portal).
2. Enters email + password -> signs in. Portal shows tenant's logo/name (branding per FR-1.5).
3. Dashboard shows list of their projects with progress % and balance summary.
4. Clicks a project -> Project Detail: milestone list (read-only statuses), financial summary, comment thread.
5. Clicks Invoices tab or a linked invoice -> Invoice Detail: line items, status badge, paid amount, balance due, payment history. PDF download available.
6. Returns to Project Detail -> Comments section. Reads existing shared comments. Types a message -> posts. Message appears with "Client" author type label.
7. Internal-only comments (posted by tenant staff) are invisible -- not rendered in client view at all.

## States & visual indicators

### Invoice lifecycle badges

| Status | Badge color | Text | Notes |
|---|---|---|---|
| Draft | Muted/outline | "Draft" | Editable, no number assigned yet |
| Issued / Sent | Blue | "Issued" | Locked, number assigned |
| Partially Paid | Yellow/amber | "Partially Paid" | Some but not all amount covered |
| Paid | Green | "Paid" | Fully paid |
| Overdue | Red | "Overdue" | Past due date and unpaid/partially paid |
| Void / Cancelled | Gray/strikethrough | "Void" | Cancelled after issue |

Badges convey status via text label AND color. Color never sole indicator (WCAG).

### Milestone status indicators

| Status | Visual cue |
|---|---|
| Pending | Gray dot or empty circle |
| In Progress | Blue dot with spinner or hourglass icon |
| Completed | Green checkmark |
| Blocked | Red diamond or warning icon |

### Empty states

- **No clients yet:** Headline "No clients yet" + description "Add your first client to get started" + CTA button "Create Client".
- **No projects yet:** Headline "No projects yet" + description "Create a project to track work for a client" + CTA "Create Project".
- **No invoices yet:** Headline "No invoices yet" + description "Invoices appear here once you create them from a project" + (no CTA if no projects exist yet; if projects exist, CTA "Create Invoice").
- **No comments yet:** "No comments yet. Start the conversation."
- **Empty search results:** "No results match your search. Try different filters."

### Disabled-feature state (feature flag off)

- Feature entry point hidden entirely (preferred) OR visible but non-interactive with upsell text.
- Example: if `client_portal_payments` disabled, payment-related UI (balance display still OK per FR-9.5) but "Pay Online" button absent. If `multi_service_projects` disabled, project creation forces single service selection.
- When a flagged feature IS visible but disabled: show muted UI + "This feature is not available on your current plan. Contact your administrator to upgrade." (FR-3.4).
- Interactive elements rendered as `<span>` or `<div>` with `aria-disabled="true"`, not actual buttons/links, to prevent interaction.

### Archived client state

- Archived client hidden from default client list (toggled via "Show archived" filter).
- Client detail shows `Archived` status badge.
- Archived client cannot be assigned to new projects.
- Archived client's users see login denial (FR-5.8): "Your account has been deactivated. Contact your service provider."

### Suspended tenant login state

- All users (admin and client) of suspended tenant see login denial on attempt: "This account has been suspended. Contact support." (FR-1.3).
- Super Admin sees tenant status `Suspended` in tenant list/detail. No tenant data leakage to login screen.

## Visibility & access control in UI

| Rule | Implementation |
|---|---|
| Internal-only comments never rendered in Client Portal | Server filters comments by `visibility` field before sending to client API. Client Portal code does not render internal-only comment markup or data. |
| Client notes/tags internal-only | Notes field on Client detail not exposed via Client Portal API. Client Profile screen omits notes and tags sections entirely. |
| Employee role sees no financial screens | Invoice List, Invoice Detail, Record Payment, Project financial summary sections -- hidden from Employee. Employee sees milestones, comments, project name/status only. |
| Client Users see only their own Client's data | Every query scoped to the Client User's `client_id`. No cross-client dropdown or list. Filtered at API query level, not just UI. |
| Manager cannot manage users or tenant settings | "Staff Users" and "Tenant Settings" tabs absent/hidden. API returns 403 if direct URL accessed. |
| Super Admin sees zero tenant operational data | Super Admin Console contains no references to clients, projects, invoices, or comments. API deny at middleware level. |

## Layout & responsive behavior

### Admin / Ops Portal

- **Desktop-first.** Primary interaction via large screens (1280px+).
- **Navigation:** Top nav (tenant name/logo, primary sections) + optional collapsible sidebar for sub-navigation. Breadcrumbs for deep drill-down.
- **Data display:** Tables for lists (clients, projects, invoices, users). Column sorting, text search, status filter chips. Pagination for large datasets.
- **Detail views:** Tabbed panels or left-detail split. Forms in panels or modal drawers.
- **Responsive:** Tables collapse to stacked card layout below `lg` breakpoint. Sidebar hides behind hamburger menu. Keep readability on tablet; mobile is secondary.

### Client Portal

- **Mobile-friendly first.** Simple single-column layout. Primary navigation via bottom tab bar or top hamburger.
- **Few screens:** Dashboard (project list cards), Project Detail (vertical scroll: milestones, financial summary, comments). Invoice list as simple card list.
- **Minimal form inputs.** Mostly read-only with occasional comment textarea and limited profile edit.

### Tenant branding

- **Placeholder theming hook:** Client Portal and login page read `tenant.logo_url` and `tenant.business_name` for header/logo display.
- Full white-label (custom colors, fonts, domain) is Phase 2. MVP rendering: render logo image + business name in header, default Tailwind colors for rest.
- Admin/Ops Portal uses platform default branding, not tenant-specific branding.

## Accessibility (extended)

In addition to WCAG 2.1 AA baseline (existing section):

- **Badges and status indicators:** Text label always present. Color is supplementary, never sole differentiator. Use `role="status"` or `aria-label` for dynamic status changes.
- **Table row actions:** Provide visible text labels OR `aria-label` for icon-only action buttons (edit, delete, issue).
- **Loading states:** Skeleton tables (keep column structure) for data lists; skeleton cards for detail views. Spinner + `aria-busy="true"` on parent region.
- **Empty state regions:** Semantic `<section>` with heading and `aria-label="No items"` pattern.
- **Error state in modals/dialogs:** Focus trap, error summary at top, `aria-describedby` linking description.
- **Keyboard flow:** All forms navigable via Tab in logical order. Submit on Enter. Cancel via Escape.
- **Color contrast on badges:** Text-to-badge-background ratio >= 3:1 minimum; 4.5:1 preferred.
- **Announce dynamic updates:** Use `aria-live="polite"` region for toast notifications, status auto-updates (invoice status change after payment recorded).**