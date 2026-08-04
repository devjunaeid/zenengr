"""add_profile_password_activity

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
Create Date: 2026-08-04 12:00:00.000000

FEAT-011 (TODO-109/113/114/115/119):
- admin_users + client_users: profile columns (avatar_url, phone, timezone, language)
- client_password_reset_tokens: client portal self-service reset tokens
- user_activities: append-only per-user activity log (polymorphic user)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Profile columns: admin_users
    op.add_column("admin_users", sa.Column("avatar_url", sa.String(length=512), nullable=True))
    op.add_column("admin_users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("admin_users", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.add_column("admin_users", sa.Column("language", sa.String(length=10), nullable=True))

    # Profile columns: client_users
    op.add_column("client_users", sa.Column("avatar_url", sa.String(length=512), nullable=True))
    op.add_column("client_users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("client_users", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.add_column("client_users", sa.Column("language", sa.String(length=10), nullable=True))

    # Client password reset tokens
    op.create_table(
        "client_password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["client_user_id"],
            ["client_users.id"],
            name=op.f("fk_client_password_reset_tokens_client_user_id_client_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_password_reset_tokens")),
    )
    op.create_index(
        op.f("ix_client_password_reset_tokens_token_hash"),
        "client_password_reset_tokens",
        ["token_hash"],
        unique=True,
    )

    # User activity log (append-only)
    op.create_table(
        "user_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_type", sa.String(length=20), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("old_value", sa.String(length=255), nullable=True),
        sa.Column("new_value", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_user_activities_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_activities")),
    )
    op.create_index(
        op.f("ix_user_activities_user_id"), "user_activities", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_activities_user_id"), table_name="user_activities")
    op.drop_table("user_activities")

    op.drop_index(
        op.f("ix_client_password_reset_tokens_token_hash"),
        table_name="client_password_reset_tokens",
    )
    op.drop_table("client_password_reset_tokens")

    op.drop_column("client_users", "language")
    op.drop_column("client_users", "timezone")
    op.drop_column("client_users", "phone")
    op.drop_column("client_users", "avatar_url")

    op.drop_column("admin_users", "language")
    op.drop_column("admin_users", "timezone")
    op.drop_column("admin_users", "phone")
    op.drop_column("admin_users", "avatar_url")
