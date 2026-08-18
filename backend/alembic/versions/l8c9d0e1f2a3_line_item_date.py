"""line_item_date

Revision ID: l8c9d0e1f2a3
Revises: k7b8c9d0e1f2
Create Date: 2026-08-18 12:00:00.000000

Invoice line items gain an entry_date (service added date / custom entry
date). Nullable so pre-existing rows are untouched.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l8c9d0e1f2a3"
down_revision: str | None = "k7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invoice_line_items",
        sa.Column("entry_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoice_line_items", "entry_date")
