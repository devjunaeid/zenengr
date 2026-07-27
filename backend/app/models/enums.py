"""Shared enum types for ORM models."""

from __future__ import annotations

import enum


class TenantStatus(enum.StrEnum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class BillingCycle(enum.StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class PermissionLevel(enum.StrEnum):
    SUPER_ADMIN_ONLY = "super_admin_only"
    TENANT_ADMIN_EDITABLE = "tenant_admin_editable"
    TENANT_ADMIN_VIEWABLE = "tenant_admin_viewable"


class ActorType(enum.StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN_USER = "admin_user"
    CLIENT_USER = "client_user"
    SYSTEM = "system"


class AdminUserRole(enum.StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class InviteRole(enum.StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
