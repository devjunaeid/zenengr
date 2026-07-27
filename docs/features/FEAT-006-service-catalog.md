---
id: FEAT-006
title: Service Catalog & Milestones
status: approved
priority: P0
source: docs/prd.md §6.6
---

# FEAT-006 — Service Catalog & Milestones

## Goal

Let tenant staff define a catalog of services with configurable milestone step templates. When a service is attached to a project, the template is instantiated into concrete project milestones with status tracking. Template changes do not retroactively affect existing project milestone instances.

## Scope

### In Scope
- Service definition: name, description, default price, ordered milestone step template
- Milestone step template: name, sequence order, expected duration/offset, description
- Fully configurable milestone structure per service (different number and ordering)
- Template instantiation into Project Milestones on project attachment
- Milestone statuses: Pending, In Progress, Completed, Blocked
- Planned/target date, actual completion date, assigned admin user per milestone
- Template immutability after instantiation (FR-6.5)
- Milestone status visible read-only on Client Portal

### Out of Scope
- Strict sequential milestone completion enforcement (per PRD Assumption 5: flexible ordering)
- Milestone-level comments (Phase 2, per FR-10.4)
- Milestone-triggered auto-invoicing (Phase 2, per PRD §7)
- Client-side milestone approval/sign-off (Phase 2, per §3.2)

## Functional Requirements

- FR-6.1: Tenant Admin/Manager can create a Service with: name, description, default price (optional), and an ordered list of **Milestone Steps** (template).
- FR-6.2: Each Milestone Step (template level) has: name, sequence order, expected duration or relative offset (optional), and description.
- FR-6.3: Each Service can define a **different number and structure** of milestone steps — fully configurable per service.
- FR-6.4: When a Service is attached to a Project, the milestone template is **instantiated** into concrete Project Milestones, each with: Status (`Pending`, `In Progress`, `Completed`, `Blocked`), planned/target date, actual completion date, assigned admin user (optional).
- FR-6.5: Editing the Service template after instantiation must **not** retroactively alter already-instantiated project milestones — only new instantiations use the updated template.
- FR-6.6: Milestone status changes are visible to the Client Portal (read-only) so clients can track delivery progress in real time.

## Acceptance Criteria

1. Tenant Admin/Manager can create a Service with name, description, default price, and ordered milestone steps.
2. Each milestone step in the template has name, sequence order, optional duration, and description.
3. Two different services can have different milestone counts and structures.
4. Attaching a service to a project instantiates milestones with Pending status and planned dates derived from the template.
5. Editing the service template after instantiation does NOT change already-instantiated project milestones.
6. A new project using the edited service gets the updated template.
7. Milestone status can be set to Pending, In Progress, Completed, or Blocked in any order (non-sequential).
8. Client Portal shows milestone statuses as read-only for the client's projects.

## Dependencies

- FEAT-001 (Tenant Management) — services are tenant-scoped
- FEAT-007 (Project Management) — service instantiation happens at project creation
- FEAT-011 (Profile Self-Service) — milestone assignment references admin users

## Decisions

- **Milestone statuses fixed enum:** Pending, In Progress, Completed, Blocked.
- **Strict sequential completion NOT enforced** per PRD Assumption 5: flexible ordering allowed.
- **Template/instance separation per FR-6.5:** editing template does not retroactively alter project milestones.
