"""Role-based permission matrix per FR-4.2.

Data-driven immutable mappings:
- TENANT_PERMISSIONS: tenant-scoped roles (admin, manager, employee)
- PLATFORM_PERMISSIONS: super_admin platform-level access

Actions vocabulary: view, manage, manage_assigned, post, edit

FEAT-016 part 2 (TODO-162): DB-backed enforcement lives alongside the
static matrix. The matrix remains the seed source for system roles and the
permission catalog; runtime checks for users with a role_id go through
role_has_permission (role_permissions rows, cached per role).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AdminUserRole
from app.models.role import Role, RolePermission

# ── Type aliases ──────────────────────────────────────────────────────────

Action = str
Resource = str
PermissionEntry = tuple[Action, Resource]

# ── Tenant-scoped permissions (admin / manager / employee) ────────────────
# FR-4.2 matrix encoded as role → frozenset of (action, resource) tuples.

_TENANT_MATRIX: dict[AdminUserRole, frozenset[PermissionEntry]] = {
    AdminUserRole.ADMIN: frozenset(
        {
            ("manage", "tenant_settings"),
            ("manage", "admin_users"),
            ("view", "admin_users"),
            ("manage", "clients"),
            ("manage", "services"),
            ("manage", "projects"),
            ("manage", "milestones"),
            ("manage", "invoices"),
            ("manage", "payments"),
            ("manage", "financial_reports"),
            ("post", "comments"),
            ("edit", "comments"),
            ("manage", "profile"),
            ("view", "files"),
            ("manage", "files"),
            ("manage", "roles"),
            ("view", "roles"),
        }
    ),
    AdminUserRole.MANAGER: frozenset(
        {
            ("view", "admin_users"),
            ("manage", "clients"),
            ("manage", "services"),
            ("manage", "projects"),
            ("manage", "milestones"),
            ("manage", "invoices"),
            ("manage", "payments"),
            ("post", "comments"),
            ("edit", "comments"),
            ("view", "financial_reports"),
            ("manage", "profile"),
            ("view", "files"),
            ("manage", "files"),
            ("manage", "roles"),
            ("view", "roles"),
        }
    ),
    AdminUserRole.EMPLOYEE: frozenset(
        {
            ("view", "clients"),
            ("view", "services"),
            ("manage_assigned", "projects"),
            ("manage_assigned", "milestones"),
            ("post", "comments"),
            ("manage", "profile"),
            ("view", "files"),
            ("view", "roles"),
        }
    ),
}

# ── Platform-level (super_admin) ──────────────────────────────────────────
# Separate set — not in tenant matrix.

_PLATFORM_RESOURCES: frozenset[PermissionEntry] = frozenset(
    {
        ("manage", "tenants"),
        ("manage", "plans"),
        ("manage", "subscriptions"),
        ("manage", "feature_flags"),
        ("manage", "platform_audit"),
    }
)


# ── Permission catalog (exported for the UI) ──────────────────────────────


def _humanize(value: str) -> str:
    """Humanize an action/resource token: 'manage_assigned' -> 'Manage Assigned'."""
    return value.replace("_", " ").title()


_PERMISSION_PAIRS: set[PermissionEntry] = set()
for _perms in _TENANT_MATRIX.values():
    _PERMISSION_PAIRS.update(_perms)

PERMISSION_CATALOG: list[dict[str, str]] = [
    {
        "action": action,
        "resource": resource,
        "label": _humanize(f"{action} {resource}"),
        "group": _humanize(resource),
    }
    for action, resource in sorted(_PERMISSION_PAIRS)
]

# ── Project-Scoped Permission Matrix & Catalog ────────────────────────────

_PROJECT_ALL_PERMISSIONS: frozenset[PermissionEntry] = frozenset(
    {
        ("view", "project_overview"),
        ("manage", "project_overview"),
        ("view", "milestones"),
        ("manage", "milestones"),
        ("view", "services"),
        ("manage", "services"),
        ("view", "invoices"),
        ("manage", "invoices"),
        ("view", "purchases"),
        ("manage", "purchases"),
        ("view", "ledger"),
        ("manage", "ledger"),
        ("view", "files"),
        ("manage", "files"),
        ("view", "comments"),
        ("post", "comments"),
        ("edit", "comments"),
        ("view", "team"),
        ("manage", "team"),
    }
)

SYSTEM_PROJECT_ROLE_PERMISSIONS: dict[str, frozenset[PermissionEntry]] = {
    "lead": _PROJECT_ALL_PERMISSIONS,
    "contributor": frozenset(
        {
            ("view", "project_overview"),
            ("view", "milestones"),
            ("manage", "milestones"),
            ("view", "services"),
            ("view", "files"),
            ("manage", "files"),
            ("view", "comments"),
            ("post", "comments"),
            ("edit", "comments"),
            ("view", "team"),
        }
    ),
    "finance": frozenset(
        {
            ("view", "project_overview"),
            ("view", "invoices"),
            ("manage", "invoices"),
            ("view", "purchases"),
            ("manage", "purchases"),
            ("view", "ledger"),
            ("manage", "ledger"),
            ("view", "milestones"),
            ("view", "services"),
            ("view", "files"),
            ("view", "comments"),
            ("post", "comments"),
            ("view", "team"),
        }
    ),
    "viewer": frozenset(
        {
            ("view", "project_overview"),
            ("view", "milestones"),
            ("view", "services"),
            ("view", "invoices"),
            ("view", "purchases"),
            ("view", "ledger"),
            ("view", "files"),
            ("view", "comments"),
            ("view", "team"),
        }
    ),
}

PROJECT_PERMISSION_CATALOG: list[dict[str, str]] = [
    {
        "action": action,
        "resource": resource,
        "label": _humanize(f"{action} {resource}"),
        "group": _humanize(resource),
    }
    for action, resource in sorted(_PROJECT_ALL_PERMISSIONS)
]


# ── DB-backed role permission cache (FEAT-016, TODO-162) ───────────────────

# role_id -> frozenset of granted "action.resource" keys. Invalidation is
# explicit: every role mutation clears the whole cache (clear_permission_cache).
ROLE_PERMISSION_CACHE: dict[uuid.UUID, frozenset[str]] = {}


def clear_permission_cache() -> None:
    """Drop all cached role permission sets (call after any role mutation)."""
    ROLE_PERMISSION_CACHE.clear()


async def role_has_permission(
    session: AsyncSession,
    *,
    role: Role,
    action: str,
    resource: str,
) -> bool:
    """Check DB-backed granted permission for a role row.

    Bypass: roles named "super_admin" or "admin" always grant (platform
    and full-tenant-access roles carry no deny rows by design). Other
    roles are resolved from role_permissions rows, cached per role_id as a
    frozenset of "action.resource" keys; a missing cache entry triggers a
    query, an empty result caches an empty set.
    """
    if role.name in ("super_admin", "admin"):
        return True

    key = f"{action}.{resource}"
    granted = ROLE_PERMISSION_CACHE.get(role.id)
    if granted is None:
        stmt = select(RolePermission).where(RolePermission.role_id == role.id)
        rows = (await session.execute(stmt)).scalars().all()
        granted = frozenset(f"{p.action}.{p.resource}" for p in rows if p.granted)
        ROLE_PERMISSION_CACHE[role.id] = granted
    return key in granted


# ── Static matrix API ─────────────────────────────────────────────────────


def has_permission(role: AdminUserRole, action: str, resource: str) -> bool:
    """Check if role has given action on resource in tenant matrix.

    Super admin is NOT in the tenant matrix — call platform_has_permission
    for super admin checks.
    """
    perms = _TENANT_MATRIX.get(role)
    if perms is None:
        return False
    return (action, resource) in perms


def platform_has_permission(action: str, resource: str) -> bool:
    """Check super-admin platform-level permission."""
    return (action, resource) in _PLATFORM_RESOURCES
