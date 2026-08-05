"""add_tenant_smtp_config

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-08-05 12:30:00.000000

FEAT-013 (per-tenant SMTP sending, TODO-138):
- smtpsecuritymode enum (NONE / STARTTLS / SSL)
- tenant_smtp_configs table: one row per tenant holding SMTP host/port/
  credentials (password stored as Fernet ciphertext), security mode,
  sender identity, and enabled flag.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUM_NAME = "smtpsecuritymode"


def _create_enum_if_not_exists(name: str, values: list[str]) -> None:
    """Create PG enum type idempotently (PG16 compatible DO block)."""
    vals = ", ".join(f"'{v}'" for v in values)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                CREATE TYPE {name} AS ENUM ({vals});
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    _create_enum_if_not_exists(_ENUM_NAME, ["NONE", "STARTTLS", "SSL"])
    smtpsecuritymode = postgresql.ENUM(
        "NONE", "STARTTLS", "SSL", name=_ENUM_NAME, create_type=False
    )
    smtpsecuritymode._create_events = False  # noqa: SLF001

    op.create_table(
        "tenant_smtp_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password_ciphertext", sa.Text(), nullable=True),
        sa.Column("from_email", sa.String(length=255), nullable=True),
        sa.Column("from_name", sa.String(length=255), nullable=True),
        sa.Column("mode", smtpsecuritymode, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
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
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tenant_smtp_configs_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_smtp_configs")),
        sa.UniqueConstraint("tenant_id", name=op.f("uq_tenant_smtp_configs_tenant_id")),
    )


def downgrade() -> None:
    op.drop_table("tenant_smtp_configs")
    op.execute(f"DROP TYPE IF EXISTS {_ENUM_NAME} CASCADE")
