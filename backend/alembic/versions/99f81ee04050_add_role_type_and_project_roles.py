"""add_role_type_and_project_roles

Revision ID: 99f81ee04050
Revises: 99f81ee04049
Create Date: 2026-08-30 22:20:00.000000
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = '99f81ee04050'
down_revision: Union[str, None] = '99f81ee04049'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('roles', sa.Column('role_type', sa.String(length=32), nullable=False, server_default='user'))


def downgrade() -> None:
    op.drop_column('roles', 'role_type')
