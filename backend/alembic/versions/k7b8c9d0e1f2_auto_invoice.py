"""auto_invoice

Revision ID: k7b8c9d0e1f2
Revises: j6a7b8c9d0e1
Create Date: 2026-08-16 09:00:00.000000

Per-project AUTO-INVOICE (TODO: FEAT): projects gain an opt-in
auto_invoice flag. When enabled, an open draft invoice is kept in sync
as services are attached (auto-created, auto-appended).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k7b8c9d0e1f2"
down_revision: str | None = "j6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "auto_invoice",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "auto_invoice")
