---
id: FEAT-010
title: Comments / Communication
status: approved
priority: P0
source: docs/prd.md §6.10
---

# FEAT-010 — Comments / Communication

## Goal

Provide project-level communication threads where tenant staff and client users can post messages. Support internal-only comments (tenant-side only) versus shared comments (visible on both portals). Basic email notification on new comments, respecting visibility scope.

## Scope

### In Scope
- Per-project comment thread with author, author type (tenant/client), timestamp, content
- Internal-only comments (tenant staff only, invisible to client portal)
- Shared comments (visible on both Admin Portal and Client Portal)
- Project-level threads (not milestone-level in MVP)
- Basic email notification on new comments, respecting internal/shared visibility

### Out of Scope
- Milestone-level threading (Phase 2 fast-follow per FR-10.4)
- File attachments in comments (Phase 2 candidate)
- Real-time chat / WebSocket (Phase 2 candidate)
- @mentions with notification routing (Phase 2 candidate)

## Functional Requirements

- FR-10.1: Each Project has a comment/activity thread where Tenant users and Client Users can post messages.
- FR-10.2: Comments record author, author type (tenant/client), timestamp, content.
- FR-10.3: Support **internal-only comments** (tenant-side only) versus **shared comments** (both portals).
- FR-10.4: MVP scope: Project-level threads (Milestone-level threading is a fast-follow).
- FR-10.5: Basic email notification on new comment, respecting internal/shared visibility.

## Acceptance Criteria

1. Tenant Admin/Manager/Employee can post a comment on a project thread.
2. Client User can post a comment on a project thread visible to them.
3. Tenant staff can mark a comment as "internal-only"; it does NOT appear in Client Portal.
4. Client User cannot see internal-only comments in any view.
5. Comments show author name, author type, and timestamp.
6. Email notification sent to relevant participants when a new shared comment is posted.
7. Email notification NOT sent for internal-only comments.
8. Project thread is accessible from both Admin Portal and Client Portal (scoped appropriately).

## Dependencies

- FEAT-001 (Tenant Management) — comments are tenant-scoped
- FEAT-004 (User & Access Management) — author attribution to admin user or client user
- FEAT-007 (Project Management) — threads are per-project

## Decisions

- **Project-level threads in MVP**; internal-only vs shared visibility distinction is required.
