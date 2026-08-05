"""add_ledger_advances

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-08-05 15:00:00.000000

FEAT-015 part 2 (transaction direction + refunds + advances, TODO-154/155):
- transactions.direction: DEBIT (payment) / CREDIT (refund); existing rows
  are backfilled as DEBIT (server_default 'DEBIT')
- payment_allocations.transaction_id becomes nullable so advance-backed
  allocations can reference an advance instead of a transaction
- advances table: client-scoped (or unassigned) advance balances created
  from payment overages
- payment_allocations.advance_id: nullable FK to advances

Downgrade reverses all of the above (transaction_id restored to NOT NULL).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_direction_enum = sa.Enum("DEBIT", "CREDIT", name="transactiondirection")


def upgrade() -> None:
    _direction_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "transactions",
        sa.Column(
            "direction",
            _direction_enum,
            nullable=False,
            server_default="DEBIT",
        ),
    )

    op.alter_column(
        "payment_allocations",
        "transaction_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    op.create_table(
        "advances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("remaining_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("source_invoice_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_type", sa.String(length=20), nullable=False),
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
            name=op.f("fk_advances_tenant_id_tenants"),
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name=op.f("fk_advances_client_id_clients"),
        ),
        sa.ForeignKeyConstraint(
            ["source_invoice_id"],
            ["invoices.id"],
            name=op.f("fk_advances_source_invoice_id_invoices"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_advances")),
    )
    op.create_index(op.f("ix_advances_tenant_id"), "advances", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_advances_client_id"), "advances", ["client_id"], unique=False)

    op.add_column(
        "payment_allocations",
        sa.Column("advance_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_payment_allocations_advance_id_advances"),
        "payment_allocations",
        "advances",
        ["advance_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_payment_allocations_advance_id_advances"),
        "payment_allocations",
        type_="foreignkey",
    )
    op.drop_column("payment_allocations", "advance_id")

    op.drop_index(op.f("ix_advances_client_id"), table_name="advances")
    op.drop_index(op.f("ix_advances_tenant_id"), table_name="advances")
    op.drop_table("advances")

    op.alter_column(
        "payment_allocations",
        "transaction_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    op.drop_column("transactions", "direction")
    sa.Enum(name="transactiondirection").drop(op.get_bind(), checkfirst=True)
