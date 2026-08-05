"""invoice_project_nullable

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-08-05 14:00:00.000000

FEAT-015 part 1 (general/internal invoices, TODO-152):
- invoices.project_id becomes nullable. A NULL project_id marks a GENERAL
  (internal) invoice with no project and no client link; such invoices only
  accept custom line items (enforced in the service layer).

Downgrade restores NOT NULL. If any general-invoice rows (NULL project_id)
exist, the downgrade will fail with a NOT NULL violation - that is
acceptable and intentional; general invoices are a one-way door until a
cleanup strategy is defined.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("invoices", "project_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.alter_column("invoices", "project_id", existing_type=sa.Uuid(), nullable=False)
