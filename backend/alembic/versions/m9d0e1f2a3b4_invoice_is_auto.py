"""invoice_is_auto

Revision ID: m9d0e1f2a3b4
Revises: l8c9d0e1f2a3
Create Date: 2026-08-18 13:00:00.000000

Auto-generated (statement) invoices are flagged is_auto so client-facing
endpoints can exclude them. Pre-existing rows default to False (manual).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m9d0e1f2a3b4"
down_revision: str | None = "l8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("is_auto", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("invoices", "is_auto")
