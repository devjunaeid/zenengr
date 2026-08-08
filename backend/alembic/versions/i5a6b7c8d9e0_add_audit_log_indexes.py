"""add_audit_log_indexes

Revision ID: i5a6b7c8d9e0
Revises: h4a5b6c7d8e9
Create Date: 2026-08-08 09:00:00.000000

Audit log query indexes:
- ix_audit_logs_tenant_created (tenant_id, created_at) serves tenant-scoped
  listing ordered by created_at desc. Platform-scope listing (tenant_id
  IS NULL) is served by the same composite index (leading column matches
  the IS NULL predicate; created_at still sorts within the group).
- ix_audit_logs_tenant_action (tenant_id, action) serves the action-prefix
  filter (action LIKE 'prefix%') scoped per tenant.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i5a6b7c8d9e0"
down_revision: str | None = "h4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_audit_logs_tenant_created"),
        "audit_logs",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_tenant_action"),
        "audit_logs",
        ["tenant_id", "action"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_tenant_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_tenant_created"), table_name="audit_logs")
