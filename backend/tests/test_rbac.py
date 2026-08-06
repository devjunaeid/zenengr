"""Exhaustive RBAC matrix tests per FR-4.2."""

from __future__ import annotations

import pytest

from app.models.enums import AdminUserRole
from app.services.permissions import has_permission, platform_has_permission

# ── FR-4.2 matrix: (role, action, resource) -> expected bool ─────────────

MATRIX: list[tuple[AdminUserRole, str, str, bool]] = [
    # Admin: manage everything
    (AdminUserRole.ADMIN, "manage", "tenant_settings", True),
    (AdminUserRole.ADMIN, "manage", "admin_users", True),
    (AdminUserRole.ADMIN, "view", "admin_users", True),
    (AdminUserRole.ADMIN, "manage", "clients", True),
    (AdminUserRole.ADMIN, "manage", "services", True),
    (AdminUserRole.ADMIN, "manage", "projects", True),
    (AdminUserRole.ADMIN, "manage", "milestones", True),
    (AdminUserRole.ADMIN, "manage", "invoices", True),
    (AdminUserRole.ADMIN, "manage", "payments", True),
    (AdminUserRole.ADMIN, "manage", "financial_reports", True),
    (AdminUserRole.ADMIN, "post", "comments", True),
    (AdminUserRole.ADMIN, "edit", "comments", True),
    (AdminUserRole.ADMIN, "manage", "profile", True),
    # Manager: manage clients/services/projects/milestones/invoices/payments; post/edit comments
    (AdminUserRole.MANAGER, "manage", "clients", True),
    (AdminUserRole.MANAGER, "manage", "services", True),
    (AdminUserRole.MANAGER, "manage", "projects", True),
    (AdminUserRole.MANAGER, "manage", "milestones", True),
    (AdminUserRole.MANAGER, "manage", "invoices", True),
    (AdminUserRole.MANAGER, "manage", "payments", True),
    (AdminUserRole.MANAGER, "post", "comments", True),
    (AdminUserRole.MANAGER, "edit", "comments", True),
    (AdminUserRole.MANAGER, "view", "financial_reports", True),
    (AdminUserRole.MANAGER, "manage", "profile", True),
    # Manager: view admin_users, but not manage
    (AdminUserRole.MANAGER, "view", "admin_users", True),
    (AdminUserRole.MANAGER, "manage", "admin_users", False),
    # Manager: no tenant_settings
    (AdminUserRole.MANAGER, "manage", "tenant_settings", False),
    # Manager: no manage on financial_reports (only view)
    (AdminUserRole.MANAGER, "manage", "financial_reports", False),
    # Employee: view clients, view services
    (AdminUserRole.EMPLOYEE, "view", "clients", True),
    (AdminUserRole.EMPLOYEE, "view", "services", True),
    # Employee: manage_assigned projects/milestones; post comments
    (AdminUserRole.EMPLOYEE, "manage_assigned", "projects", True),
    (AdminUserRole.EMPLOYEE, "manage_assigned", "milestones", True),
    (AdminUserRole.EMPLOYEE, "post", "comments", True),
    (AdminUserRole.EMPLOYEE, "edit", "comments", False),
    # Employee: manage profile
    (AdminUserRole.EMPLOYEE, "manage", "profile", True),
    # Employee: blocked
    (AdminUserRole.EMPLOYEE, "manage", "clients", False),
    (AdminUserRole.EMPLOYEE, "manage", "services", False),
    (AdminUserRole.EMPLOYEE, "manage", "projects", False),
    (AdminUserRole.EMPLOYEE, "manage", "invoices", False),
    (AdminUserRole.EMPLOYEE, "manage", "payments", False),
    (AdminUserRole.EMPLOYEE, "view", "invoices", False),
    (AdminUserRole.EMPLOYEE, "view", "financial_reports", False),
    (AdminUserRole.EMPLOYEE, "manage", "financial_reports", False),
    (AdminUserRole.EMPLOYEE, "manage", "tenant_settings", False),
    (AdminUserRole.EMPLOYEE, "view", "admin_users", False),
    (AdminUserRole.EMPLOYEE, "manage", "admin_users", False),
]


class TestRBACMatrix:
    @pytest.mark.parametrize("role,action,resource,expected", MATRIX)
    def test_tenant_permissions(self, role, action, resource, expected):
        assert has_permission(role, action, resource) is expected


class TestPlatformPermissions:
    def test_super_admin_platform_access(self):
        assert platform_has_permission("manage", "tenants") is True
        assert platform_has_permission("manage", "plans") is True
        assert platform_has_permission("manage", "subscriptions") is True
        assert platform_has_permission("manage", "feature_flags") is True
        assert platform_has_permission("manage", "platform_audit") is True

    def test_unknown_resource(self):
        assert platform_has_permission("manage", "clients") is False


class TestUnknownRole:
    def test_unknown_role_denied(self):
        # has_permission accepts AdminUserRole enum; test edge
        result = has_permission(AdminUserRole.SUPER_ADMIN, "manage", "tenants")
        # Super admin not in tenant matrix -> False
        assert result is False
