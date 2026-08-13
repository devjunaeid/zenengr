"""add_ledger_entries

Revision ID: j6a7b8c9d0e1
Revises: i5a6b7c8d9e0
Create Date: 2026-08-13 09:00:00.000000

FEAT-018 part 1 (TODO-178):
- ledgerentrytype enum (CHARGE / PAYMENT / REFUND)
- ledgersourcetype enum (PROJECT_SERVICE / TRANSACTION / MANUAL_ADJUSTMENT)
- discounttype enum (PERCENTAGE / FIXED)
- ledger_entries table: append-only project ledger rows (charges + manual
  adjustments only; the payment stream is derived from Transactions at read
  time, no mirror writes). Indexes on (project_id, type) and
  (project_id, entry_date). FKs: project CASCADE, invoice SET NULL,
  admin_user (created_by) SET NULL.
- projects gains 4 nullable discount columns (discount_type, discount_value,
  discount_updated_at, discount_updated_by -> admin_users SET NULL).

Enum values are stored as the SQLAlchemy member NAMES (existing convention,
e.g. CHARGE) — the ORM persists names, not the lowercase StrEnum values.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j6a7b8c9d0e1"
down_revision: str | None = "i5a6b7c8d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def _enum(name: str, *values: str) -> postgresql.ENUM:
    e = postgresql.ENUM(*values, name=name, create_type=False)
    e._create_events = False  # noqa: SLF001
    return e


def upgrade() -> None:
    _create_enum_if_not_exists("ledgerentrytype", ["CHARGE", "PAYMENT", "REFUND"])
    _create_enum_if_not_exists(
        "ledgersourcetype",
        ["PROJECT_SERVICE", "TRANSACTION", "MANUAL_ADJUSTMENT"],
    )
    _create_enum_if_not_exists("discounttype", ["PERCENTAGE", "FIXED"])

    ledgerentrytype = _enum("ledgerentrytype", "CHARGE", "PAYMENT", "REFUND")
    ledgersourcetype = _enum(
        "ledgersourcetype",
        "PROJECT_SERVICE",
        "TRANSACTION",
        "MANUAL_ADJUSTMENT",
    )
    discounttype = _enum("discounttype", "PERCENTAGE", "FIXED")

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("type", ledgerentrytype, nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("source_type", ledgersourcetype, nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("invoice_ref", sa.Uuid(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
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
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_ledger_entries_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_ref"],
            ["invoices.id"],
            name=op.f("fk_ledger_entries_invoice_ref_invoices"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["admin_users.id"],
            name=op.f("fk_ledger_entries_created_by_id_admin_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_entries")),
    )
    op.create_index(
        op.f("ix_ledger_entries_project_type"),
        "ledger_entries",
        ["project_id", "type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ledger_entries_project_date"),
        "ledger_entries",
        ["project_id", "entry_date"],
        unique=False,
    )

    op.add_column(
        "projects",
        sa.Column("discount_type", discounttype, nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("discount_value", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("discount_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("discount_updated_by", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_projects_discount_updated_by_admin_users"),
        "projects",
        "admin_users",
        ["discount_updated_by"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_projects_discount_updated_by_admin_users"),
        "projects",
        type_="foreignkey",
    )
    op.drop_column("projects", "discount_updated_by")
    op.drop_column("projects", "discount_updated_at")
    op.drop_column("projects", "discount_value")
    op.drop_column("projects", "discount_type")

    op.drop_index(op.f("ix_ledger_entries_project_date"), table_name="ledger_entries")
    op.drop_index(op.f("ix_ledger_entries_project_type"), table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.execute("DROP TYPE IF EXISTS discounttype CASCADE")
    op.execute("DROP TYPE IF EXISTS ledgersourcetype CASCADE")
    op.execute("DROP TYPE IF EXISTS ledgerentrytype CASCADE")
