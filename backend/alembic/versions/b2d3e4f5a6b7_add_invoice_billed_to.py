"""add_invoice_billed_to

Revision ID: b2d3e4f5a6b7
Revises: 99f81ee04050
Create Date: 2026-09-09 22:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b2d3e4f5a6b7'
down_revision: Union[str, None] = '99f81ee04050'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'invoices',
        sa.Column(
            'billed_to',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default='{}',
        ),
    )


def downgrade() -> None:
    op.drop_column('invoices', 'billed_to')
