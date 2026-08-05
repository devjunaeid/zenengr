"""Role-based permission matrix per FR-4.2.

Data-driven immutable mappings:
- TENANT_PERMISSIONS: tenant-scoped roles (admin, manager, employee)
- PLATFORM_PERMISSIONS: super_admin platform-level access

Actions vocabulary: view, manage, manage_assigned
"""

from __future__ import annotations

from app.models.enums import AdminUserRole

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
            ("manage", "comments"),
            ("manage", "profile"),
            ("view", "files"),
            ("manage", "files"),
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
            ("manage", "comments"),
            ("view", "financial_reports"),
            ("manage", "profile"),
            ("view", "files"),
            ("manage", "files"),
        }
    ),
    AdminUserRole.EMPLOYEE: frozenset(
        {
            ("view", "clients"),
            ("view", "services"),
            ("manage_assigned", "projects"),
            ("manage_assigned", "milestones"),
            ("manage_assigned", "comments"),
            ("manage", "profile"),
            ("view", "files"),
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


# ── Public API ────────────────────────────────────────────────────────────


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
