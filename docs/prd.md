<!-- Source of truth. BRD v0.1, 2026-07-26. Do not edit; changes go in new versions. -->

# Business Requirements Document (BRD)
## Multi-Tenant Service, Project & Billing Management Platform — MVP

| | |
|---|---|
| **Document Status** | Draft v0.1 |
| **Prepared For** | Product / Engineering Team |
| **Scope** | MVP Release |
| **Date** | 26 July 2026 |

---

## 1. Introduction & Purpose

This document defines the business requirements for the MVP of a **multi-tenant SaaS platform** that allows service-based businesses (agencies, consultancies, studios, etc. — "Tenants") to manage their own customers ("Clients"), sell and deliver **Services** with **milestone-based progress tracking**, bundle those services into **Projects**, **invoice** clients, and track **financial transactions** including partial payments — all governed by a **Super Admin** layer that controls tenant subscriptions, settings, and feature entitlements.

The platform has two distinct audiences per tenant:
- **Tenant-side users** (Admin, Manager, Employee) who run the business.
- **Client-side users** who consume the tenant's services, view project progress, view/pay invoices, and communicate with the tenant.

---

## 2. Business Objectives

1. Allow a single platform instance to serve many independent businesses (tenants) with full data isolation.
2. Give the platform owner (Super Admin) commercial and operational control over every tenant — subscription, settings, and feature access — without touching tenant data.
3. Let each tenant manage its own team, its own clients, and its own service catalog independently.
4. Provide a structured, auditable way to sell services, deliver them via trackable milestones, bundle them into projects, and bill clients — including partial and per-service payments.
5. Give clients visibility and self-service (view progress, view invoices, pay, comment) through a dedicated portal, separate from the tenant's operational portal.

---

## 3. Scope

### 3.1 In Scope (MVP)
- Tenant provisioning, subscription & settings management (Super Admin)
- Tenant feature flag / capability management (Super Admin)
- Tenant admin-side team management with roles (Admin, Manager, Employee)
- Tenant client management + separate Client Portal with its own login
- Service catalog with configurable milestone templates
- Project creation combining one or more services, with milestone progress tracking per project
- Invoicing tied to projects/services, supporting incremental billing as scope grows
- Payment/transaction tracking, including partial and service-specific payments
- Comment/communication thread per project (tenant ↔ client)
- Admin user management (invite, roles, deactivate, audit trail)
- Customer/Client management (records, notes, activity history)
- User profile management (self-service, both Admin Portal and Client Portal users)

### 3.2 Out of Scope (MVP) — candidates for Phase 2
- Automated recurring/subscription billing to clients
- Tax engine / multi-currency accounting compliance
- Payment gateway auto-reconciliation (webhooks) — MVP can support manual transaction logging + optional single gateway
- Milestone-triggered automatic invoicing
- Contracts/e-signature module
- Time tracking / timesheets
- Advanced reporting & BI dashboards
- Client-side approvals/sign-off workflow on milestones
- Multi-language / localization
- Mobile apps (native)

---

## 4. Stakeholders & User Roles

| Role | Scope | Description |
|---|---|---|
| **Super Admin** | Platform-wide | Platform operator. Manages tenants, subscriptions, settings, feature flags. No access to tenant's operational data (clients, projects). |
| **Tenant Admin** | Tenant-wide | Full control within their tenant: users, clients, services, projects, invoices, settings (within what Super Admin allows). |
| **Tenant Manager** | Tenant-wide, restricted | Operational management: services, projects, milestones, invoices. Typically restricted from billing/subscription and user-role management. |
| **Tenant Employee** | Assigned scope | Works on assigned projects/milestones; limited visibility into financials. |
| **Client (Company/Contact)** | Own data only | The tenant's customer entity. Can have one or more Client Users. |
| **Client User** | Own client's data only | Logs into the separate Client Portal; sees only their own projects, invoices, and can comment/pay. |

**Two distinct portals/logins are required:**
- **Admin/Ops Portal** — for Super Admin, Tenant Admin, Manager, Employee.
- **Client Portal** — for Client Users only, scoped strictly to their own tenant relationship.

---

## 5. High-Level Architecture Notes (Business-Level, not technical design)

- **Multi-tenancy**: every core record (User, Client, Service, Project, Invoice, Transaction, Comment) belongs to exactly one Tenant. Tenant isolation must be enforced at every layer.
- **Two auth realms**: Admin-side auth (staff) and Client-side auth (customers) should be logically separate — separate login pages, separate session/token scopes, separate role sets — even if they share the same backend. This avoids accidental privilege leakage and lets the client-facing portal be branded/white-labeled per tenant later.
- **Super Admin sits above tenants**: it manages the container (tenant, plan, settings, features) but does not participate in day-to-day tenant operations.

---

## 6. Functional Requirements by Module

### 6.1 Module: Tenant Management

- FR-1.1: Super Admin can create, view, edit, suspend, and delete/deactivate tenants.
- FR-1.2: Each tenant has a unique identifier/slug (used for subdomain or login routing, e.g. `tenantname.platform.com` — optional for MVP, but data model should support it).
- FR-1.3: Tenant has a lifecycle status: `Trial`, `Active`, `Suspended`, `Cancelled`.
- FR-1.4: A tenant's data (clients, projects, invoices, users) is fully isolated from other tenants — no cross-tenant visibility under any tenant-side role.
- FR-1.5: Tenant Admin can view/edit their own tenant's profile info (business name, logo, contact info, branding) but cannot change subscription tier or platform-level feature flags.

### 6.2 Module: Subscription & Tenant Settings (Super Admin controlled)

- FR-2.1: Super Admin can assign a subscription **Plan** to a tenant (e.g., Free/Trial, Starter, Pro, Enterprise).
- FR-2.2: Each Plan defines default limits (e.g., max admin users, max clients, max active projects, max storage) — MVP can ship a small set of plans; limits should be data-driven, not hardcoded in code, so Super Admin can adjust them.
- FR-2.3: Super Admin can view/edit a tenant's subscription status (active, past due, cancelled), billing cycle, and renewal date. (MVP: manually tracked by Super Admin; automated billing of tenants is Phase 2.)
- FR-2.4: Tenant Settings (distinct from subscription) include operational configuration such as default currency, invoice numbering format, timezone, date format, email sender identity, etc. Some settings are editable by Tenant Admin; others are Super-Admin-only.
- FR-2.5: A clear permission table must define, per setting, whether it is `Super Admin only`, `Tenant Admin editable`, or `Tenant Admin viewable only`.

### 6.3 Module: Tenant Capabilities / Feature Flags (Super Admin controlled)

- FR-3.1: Super Admin can enable/disable individual **feature flags** per tenant (e.g., `client_portal_payments`, `multi_service_projects`, `comments_module`, `partial_payment_tracking`).
- FR-3.2: Feature flags should be structured as a simple key-value/boolean registry per tenant, checked by the application before rendering/allowing the related functionality.
- FR-3.3: Feature flags may optionally have a default value per Plan (e.g., Starter plan defaults `custom_branding = false`), but Super Admin can override the default per individual tenant.
- FR-3.4: Tenant-side users (including Tenant Admin) cannot self-enable a disabled feature; they can only see current capability status and (optionally) a "request upgrade" prompt.
- FR-3.5: Feature flag changes should take effect without requiring redeployment (data-driven, not code-driven).

### 6.4 Module: User & Access Management

**Admin-side users:**
- FR-4.1: Tenant Admin can invite/create users with roles: `Admin`, `Manager`, `Employee`.
- FR-4.2: Role-based permission matrix (minimum for MVP):

| Capability | Admin | Manager | Employee |
|---|---|---|---|
| Manage tenant settings | ✅ | ❌ | ❌ |
| Manage admin users/roles | ✅ | ❌ | ❌ |
| Manage clients | ✅ | ✅ | View only |
| Manage services catalog | ✅ | ✅ | View only |
| Create/manage projects | ✅ | ✅ | Assigned only |
| Update milestone status | ✅ | ✅ | Assigned only |
| Create/manage invoices | ✅ | ✅ | ❌ |
| Record payments | ✅ | ✅ | ❌ |
| View financial reports | ✅ | ✅ | ❌ |
| Post/view comments | ✅ | ✅ | Assigned only |
| Edit own profile/password | ✅ | ✅ | ✅ |
| Invite/deactivate other admin users | ✅ | ❌ | ❌ |

- FR-4.3: Admin users log in via the **Admin/Ops Portal**, distinct URL/UI from the client portal.
- FR-4.4: Deactivating an admin user must not delete their historical activity (comments, actions) — soft-delete/deactivate only.
- FR-4.9: Tenant Admin can **invite** a new admin user via email; invite flow includes role pre-assignment and expires after a defined period if unaccepted.
- FR-4.10: Tenant Admin can **edit** an existing admin user's role/permissions at any time; role changes take effect on next request (no need to re-login, ideally).
- FR-4.11: Tenant Admin can **deactivate/reactivate** an admin user. A deactivated user immediately loses portal access but their historical records remain intact and attributed to them.
- FR-4.12: Tenant Admin can trigger a **password reset** on behalf of another admin user (support scenario), separate from that user's own self-service reset (see 6.11).
- FR-4.13: System maintains a basic **audit trail** of sensitive admin actions (role changes, deactivations, invoice issuance, payment recording) — who did what and when. A simple activity log list is sufficient for MVP.
- FR-4.14: A user cannot deactivate or edit the role of the tenant's last remaining Admin.

**Client-side users:**
- FR-4.5: A Client (company/contact record) can have one or more Client Users associated with it.
- FR-4.6: Client Users log in via a separate **Client Portal**, seeing only their own Client's projects, invoices, transactions, and comments.
- FR-4.7: Tenant Admin/Manager can invite a Client User (e.g., via email invite) and optionally deactivate access.
- FR-4.8: Client Users cannot see other clients' data, other tenants, or internal-only comments (see 6.10).

### 6.5 Module: Customer / Client Management

- FR-5.1: Tenant Admin/Manager can create, edit, and view Clients (company or individual) within their tenant.
- FR-5.2: A Client record holds contact details, billing info (billing address, tax ID if applicable), and status (`Active`, `Archived`).
- FR-5.3: A Client can have multiple Client Users (contacts) but a single primary billing contact.
- FR-5.4: Client list should show summary rollups: number of active projects, total invoiced, total outstanding balance.
- FR-5.5: Tenant Admin/Manager can add free-text **notes** and simple **tags/labels** to a Client record — notes are internal-only, never visible on the Client Portal.
- FR-5.6: System maintains a basic **activity/interaction history** per Client — automatically logged events such as project created, invoice issued, payment received, comment posted.
- FR-5.7: Tenant Admin/Manager can **search and filter** the client list (by name, status, tag, outstanding balance).
- FR-5.8: Archiving a Client hides them from default active lists but preserves all historical projects/invoices; archived clients' users lose Client Portal access.
- FR-5.9: Client Users can view and update limited fields on their own Client profile (e.g., contact details) from the Client Portal — billing-sensitive fields (tax ID, billing address) require Tenant Admin/Manager edit rather than direct self-service.

### 6.6 Module: Service Catalog & Milestones

- FR-6.1: Tenant Admin/Manager can create a Service with: name, description, default price (optional), and an ordered list of **Milestone Steps** (template).
- FR-6.2: Each Milestone Step (template level) has: name, sequence order, expected duration or relative offset (optional), and description.
- FR-6.3: Each Service can define a **different number and structure** of milestone steps — fully configurable per service.
- FR-6.4: When a Service is attached to a Project, the milestone template is **instantiated** into concrete Project Milestones, each with: Status (`Pending`, `In Progress`, `Completed`, `Blocked`), planned/target date, actual completion date, assigned admin user (optional).
- FR-6.5: Editing the Service template after instantiation must **not** retroactively alter already-instantiated project milestones — only new instantiations use the updated template.
- FR-6.6: Milestone status changes are visible to the Client Portal (read-only) so clients can track delivery progress in real time.

### 6.7 Module: Project Management

- FR-7.1: Tenant Admin/Manager can create a Project for a specific Client, selecting one or more Services to include.
- FR-7.2: A Project must capture: name, associated Client, start date, status (`Draft`, `Active`, `On Hold`, `Completed`, `Cancelled`), and owner (assigned admin user).
- FR-7.3: Each Service attached to a Project becomes a **Project Service** instance, carrying its own instantiated milestones (per 6.6).
- FR-7.4: A Project must support adding **additional Services after creation** (mid-life scope growth) — see PRD §7 for billing implications.
- FR-7.5: Project overview screen (both Admin and Client Portal, scoped appropriately) must show: overall progress (aggregate of milestone completion), financial summary (total invoiced, total paid, balance due), and linked invoices.
- FR-7.6: Removing a Service from a Project after invoicing has occurred should be restricted/soft (mark as `Cancelled` rather than deleted) to preserve financial history integrity.

### 6.8 Module: Invoicing

- FR-8.1: Tenant Admin/Manager can generate an Invoice for a Project, selecting which Project Service(s) / line items to include.
- FR-8.2: Invoice must contain: invoice number (tenant-scoped sequential numbering, per FR-2.4 settings), issue date, due date, line items (each linked to a Project Service or a custom line item), subtotal, tax (optional MVP), total, and status.
- FR-8.3: Invoice status lifecycle: `Draft` → `Issued/Sent` → `Partially Paid` → `Paid` → (or `Overdue`, `Void`/`Cancelled`).
- FR-8.4: **Draft invoices are editable**; once **Issued**, core financial fields become **locked/immutable**. Corrections via a new adjustment (credit note or new invoice), never by editing history.
- FR-8.5: A Project can have **multiple invoices** over its lifetime.
- FR-8.6: Client Portal shows all invoices for their own projects with current status and balance due.
- FR-8.7: Invoices should be exportable/viewable as PDF.

### 6.9 Module: Payments & Financial Tracking

- FR-9.1: Tenant Admin/Manager can record a Transaction (payment) against an Invoice: amount, date, method (bank transfer, card, cash, other), reference note, recorded-by user.
- FR-9.2: A Transaction can be a **partial payment**. Invoice status must auto-update to `Partially Paid` when `0 < amount paid < total`, and `Paid` when fully covered.
- FR-9.3: Where an Invoice contains multiple line items, the system supports **allocating a payment across specific line items** ("how much has been paid toward Service X"). Default: system proposes proportional/FIFO auto-allocation; tenant staff can manually override.
- FR-9.4: Project-level financial summary aggregates across all invoices/transactions: Total Invoiced, Total Paid, Total Outstanding — optionally per Service.
- FR-9.5: Client Users can view payment history and outstanding balance in the Client Portal (view-only in MVP).
- FR-9.6: All financial records (invoices, transactions) are immutable once finalized — corrections via new records, never destructive edits.

### 6.10 Module: Comments / Communication

- FR-10.1: Each Project has a comment/activity thread where Tenant users and Client Users can post messages.
- FR-10.2: Comments record author, author type (tenant/client), timestamp, content.
- FR-10.3: Support **internal-only comments** (tenant-side only) versus **shared comments** (both portals).
- FR-10.4: MVP scope: Project-level threads (Milestone-level threading is a fast-follow).
- FR-10.5: Basic email notification on new comment, respecting internal/shared visibility.

### 6.11 Module: User Profile Management (Self-Service)

- FR-11.1: Every logged-in user (either portal) can view/edit own profile: name, avatar, email (re-verification on change), phone, timezone, language preference (single default OK for MVP).
- FR-11.2: Every logged-in user can change own password (current-password confirmation) and trigger a "forgot password" flow via email.
- FR-11.3: Every logged-in user can set **notification preferences** (email on: new comment, invoice issued, payment received, milestone completed) — default on, user-adjustable.
- FR-11.4: Admin-side and Client-side profile screens are visually/functionally separate but share the principle: a user only ever edits their *own* record.
- FR-11.5: Changing own email/password requires no Tenant Admin involvement, but appears in the account's own activity history (e.g., "Password changed on [date]").
- FR-11.6: Profile changes must not allow privilege escalation (Client User cannot change role or Client association; Employee cannot self-promote).

---

## 7. Critical Business Logic: Mid-Project Service Additions & Partial/Service-Level Payments

1. **Invoices decouple from Projects as 1-to-many.** A Project has multiple invoices over its lifetime.
2. **Invoices have a Draft state** — fully editable while in Draft.
3. **Once Issued, an invoice is locked.** New Services added after issuance bill via a **new invoice**, never by reopening the issued one.
4. **Payments tracked at Transaction level, linked to a specific Invoice**, with optional line-item allocation.
5. **Project financial rollups are computed, not stored** — derived by summing across invoices and transactions.
6. **MVP simplification:** milestone completion does NOT auto-trigger invoices; invoicing is a manual action. Milestones are progress tracking only in MVP.

---

## 8. High-Level Data Model

```
Tenant 1---N AdminUser
Tenant 1---1 TenantSubscription
Tenant 1---N TenantSetting
Tenant 1---N TenantFeatureFlag
Tenant 1---N Client
Client  1---N ClientUser
Tenant 1---N Service
Service 1---N MilestoneTemplateStep
Tenant 1---N Project
Project N---1 Client
Project 1---N ProjectService
ProjectService 1---N ProjectMilestone
Project 1---N Invoice
Invoice 1---N InvoiceLineItem
Invoice 1---N Transaction
Transaction 1---N PaymentAllocation (optional, maps to InvoiceLineItem)
Project 1---N Comment
Comment N---1 (AdminUser | ClientUser) as author
```

---

## 9. Non-Functional Requirements

- **Data isolation**: strict tenant-scoping on every query; no cross-tenant leakage.
- **Auditability**: financial records append-only/immutable once finalized.
- **Security**: separate auth/session for Admin Portal vs Client Portal; RBAC enforced server-side.
- **Scalability**: queries tenant-indexed.
- **Extensibility**: settings and feature flags data-driven.
- **Usability**: Client Portal minimal screens: Projects, Progress, Invoices, Comments.

---

## 10. Assumptions (confirmed)

1. Single currency per tenant for MVP.
2. Manual payment recording for MVP; online collection is a Phase 2 feature flag.
3. Tax calculation out of scope for MVP (flat totals; optional tax field).
4. One Client User login = one Tenant relationship.
5. Milestone ordering flexible — strict sequential completion NOT enforced.
6. Super Admin has NO access to tenant operational data (container-level only).
7. Milestone statuses fixed enum: Pending, In Progress, Completed, Blocked.
8. Invoice numbering: tenant-scoped gapless sequential with configurable format template.

---

*End of PRD v0.1 — confirmed baseline for MVP docs.*
