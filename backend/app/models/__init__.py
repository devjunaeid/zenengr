"""SQLAlchemy ORM models — import here for Alembic autogenerate detection."""

from app.models.admin_user import AdminUser
from app.models.advance import Advance
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.client_invite import ClientInvite
from app.models.client_note import ClientNote
from app.models.client_password_reset_token import ClientPasswordResetToken
from app.models.client_user import ClientUser
from app.models.comment import Comment
from app.models.email_verification_token import EmailVerificationToken
from app.models.enums import (
    ActorType,
    AdminUserRole,
    BillingCycle,
    ClientStatus,
    ClientType,
    CommentAuthorType,
    FileScope,
    InviteRole,
    InvoiceStatus,
    MilestoneStatus,
    NotificationEventType,
    PaymentMethod,
    PermissionLevel,
    ProjectServiceStatus,
    ProjectStatus,
    SmtpSecurityMode,
    SubscriptionStatus,
    TenantStatus,
    TransactionDirection,
)
from app.models.file_asset import FileAsset
from app.models.file_folder import FileFolder
from app.models.invite import Invite
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.invoice_number_sequence import InvoiceNumberSequence
from app.models.milestone_step_template import MilestoneStepTemplate
from app.models.notification_preference import NotificationPreference
from app.models.password_reset_token import PasswordResetToken
from app.models.plan import Plan
from app.models.plan_feature_default import PlanFeatureDefault
from app.models.project import Project
from app.models.project_milestone import ProjectMilestone
from app.models.project_service import ProjectService
from app.models.role import Role, RolePermission
from app.models.service import Service
from app.models.tenant import Tenant
from app.models.tenant_feature_flag import TenantFeatureFlag
from app.models.tenant_setting import TenantSetting
from app.models.tenant_smtp_config import TenantSmtpConfig
from app.models.tenant_subscription import TenantSubscription
from app.models.transaction import PaymentAllocation, Transaction
from app.models.user_activity import UserActivity

__all__ = [
    "Plan",
    "Tenant",
    "TenantSubscription",
    "TenantSetting",
    "TenantSmtpConfig",
    "PlanFeatureDefault",
    "TenantFeatureFlag",
    "AuditLog",
    "AdminUser",
    "Advance",
    "Invite",
    "PasswordResetToken",
    "Client",
    "ClientNote",
    "ClientUser",
    "ClientInvite",
    "Comment",
    "Invoice",
    "InvoiceLineItem",
    "InvoiceNumberSequence",
    "Service",
    "MilestoneStepTemplate",
    "Project",
    "ProjectService",
    "ProjectMilestone",
    "Role",
    "RolePermission",
    "Transaction",
    "PaymentAllocation",
    "ClientPasswordResetToken",
    "EmailVerificationToken",
    "NotificationPreference",
    "UserActivity",
    "FileFolder",
    "FileAsset",
    "ActorType",
    "AdminUserRole",
    "BillingCycle",
    "ClientStatus",
    "ClientType",
    "CommentAuthorType",
    "FileScope",
    "InviteRole",
    "InvoiceStatus",
    "MilestoneStatus",
    "NotificationEventType",
    "PaymentMethod",
    "PermissionLevel",
    "ProjectServiceStatus",
    "ProjectStatus",
    "SmtpSecurityMode",
    "SubscriptionStatus",
    "TenantStatus",
    "TransactionDirection",
]
