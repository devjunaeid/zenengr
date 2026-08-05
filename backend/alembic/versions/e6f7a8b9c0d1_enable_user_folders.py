"""enable_user_folders

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-08-05 12:00:00.000000

FEAT-012 (per-user folders in USER scope):
- created_by_id becomes nullable: TENANT/PROJECT folders are shared
  (creator NULL), USER folders carry the creator.
- Replace the plain unique constraint with a unique index whose key
  includes COALESCE(created_by_id, <null-uuid>): names are unique per
  (tenant, parent, scope, name, project_id) for shared folders, and per
  creator for USER folders.

NOTE: revision id intentionally differs from the originally specified
e5f6a7b8c9d0, which is already taken by add_transaction_tables.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_CONSTRAINT = "uq_file_folders_tenant_parent_scope_name_project"
_NEW_INDEX = "uq_file_folders_tenant_parent_scope_name_project_creator"


def upgrade() -> None:
    op.alter_column(
        "file_folders",
        "created_by_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.drop_constraint(_OLD_CONSTRAINT, "file_folders", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_file_folders_tenant_parent_scope_name_project_creator "
        "ON file_folders (tenant_id, parent_id, scope, name, project_id, "
        "COALESCE(created_by_id, '00000000-0000-0000-0000-000000000000'::uuid))"
    )


def downgrade() -> None:
    op.drop_index(_NEW_INDEX, table_name="file_folders")
    op.create_unique_constraint(
        _OLD_CONSTRAINT,
        "file_folders",
        ["tenant_id", "parent_id", "scope", "name", "project_id"],
    )
    op.alter_column(
        "file_folders",
        "created_by_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
