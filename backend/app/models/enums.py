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


class ClientType(enum.StrEnum):
    COMPANY = "company"
    INDIVIDUAL = "individual"


class CommentAuthorType(enum.StrEnum):
    TENANT_ADMIN = "tenant_admin"
    TENANT_MANAGER = "tenant_manager"
    TENANT_EMPLOYEE = "tenant_employee"
    CLIENT_USER = "client_user"


class ClientStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MilestoneStatus(enum.StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ProjectStatus(enum.StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectServiceStatus(enum.StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class InvoiceStatus(enum.StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOID = "void"


class PaymentMethod(enum.StrEnum):
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    CASH = "cash"
    OTHER = "other"


class TransactionDirection(enum.StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class NotificationEventType(enum.StrEnum):
    NEW_COMMENT = "new_comment"
    INVOICE_ISSUED = "invoice_issued"
    PAYMENT_RECEIVED = "payment_received"
    MILESTONE_COMPLETED = "milestone_completed"
    REFUND_RECORDED = "refund_recorded"
    ADVANCE_APPLIED = "advance_applied"
    PROJECT_CREATED = "project_created"


class NotificationChannel(enum.StrEnum):
    EMAIL = "email"
    INAPP = "inapp"


class FileScope(enum.StrEnum):
    USER = "user"
    TENANT = "tenant"
    PROJECT = "project"


class SmtpSecurityMode(enum.StrEnum):
    NONE = "none"
    STARTTLS = "starttls"
    SSL = "ssl"


class LedgerEntryType(enum.StrEnum):
    CHARGE = "charge"
    PAYMENT = "payment"
    REFUND = "refund"


class LedgerSourceType(enum.StrEnum):
    PROJECT_SERVICE = "project_service"
    TRANSACTION = "transaction"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class DiscountType(enum.StrEnum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"
