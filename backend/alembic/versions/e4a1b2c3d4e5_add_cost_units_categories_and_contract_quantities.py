"""add_cost_units_categories_and_contract_quantities

Revision ID: e4a1b2c3d4e5
Revises: 9dd10cbef8d3
Create Date: 2026-10-10 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a1b2c3d4e5'
down_revision: Union[str, None] = '9dd10cbef8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. purchase_entries: vendor_name
    op.add_column(
        'purchase_entries',
        sa.Column('vendor_name', sa.String(length=255), nullable=True)
    )

    # 2. purchase_entry_items: unit, category
    op.add_column(
        'purchase_entry_items',
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='unit')
    )
    op.add_column(
        'purchase_entry_items',
        sa.Column('category', sa.String(length=50), nullable=False, server_default='materials')
    )

    # 3. project_services: quantity, unit
    op.add_column(
        'project_services',
        sa.Column('quantity', sa.Numeric(precision=12, scale=2), nullable=False, server_default='1')
    )
    op.add_column(
        'project_services',
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='unit')
    )

    # 4. invoice_line_items: unit
    op.add_column(
        'invoice_line_items',
        sa.Column('unit', sa.String(length=50), nullable=False, server_default='unit')
    )


def downgrade() -> None:
    op.drop_column('invoice_line_items', 'unit')
    op.drop_column('project_services', 'unit')
    op.drop_column('project_services', 'quantity')
    op.drop_column('purchase_entry_items', 'category')
    op.drop_column('purchase_entry_items', 'unit')
    op.drop_column('purchase_entries', 'vendor_name')
