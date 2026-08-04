"""add_transactions_paymentallocations

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-08-03 10:00:00.000000

Adds payments core (FEAT-009, TODO-089/090/092/093/095):
- transactions: payment records against issued/partially-paid invoices
- payment_allocations: per-line-item distribution of a payment
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "method",
            sa.Enum(
                "BANK_TRANSFER",
                "CARD",
                "CASH",
                "OTHER",
                name="paymentmethod",
            ),
            nullable=False,
        ),
        sa.Column("reference_note", sa.Text(), nullable=False),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("fk_transactions_invoice_id_invoices"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_id"],
            ["admin_users.id"],
            name=op.f("fk_transactions_recorded_by_id_admin_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transactions")),
    )
    op.create_index(
        op.f("ix_transactions_invoice_id"), "transactions", ["invoice_id"], unique=False
    )

    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("line_item_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
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
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_payment_allocations_transaction_id_transactions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["line_item_id"],
            ["invoice_line_items.id"],
            name=op.f("fk_payment_allocations_line_item_id_invoice_line_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_allocations")),
    )
    op.create_index(
        op.f("ix_payment_allocations_transaction_id"),
        "payment_allocations",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_allocations_line_item_id"),
        "payment_allocations",
        ["line_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_payment_allocations_line_item_id"),
        table_name="payment_allocations",
    )
    op.drop_index(
        op.f("ix_payment_allocations_transaction_id"),
        table_name="payment_allocations",
    )
    op.drop_table("payment_allocations")
    op.drop_index(op.f("ix_transactions_invoice_id"), table_name="transactions")
    op.drop_table("transactions")
    sa.Enum(name="paymentmethod").drop(op.get_bind(), checkfirst=True)
