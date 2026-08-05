"""fix_file_folder_constraint

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-05 10:00:00.000000

FEAT-012 (TODO-127/128/129/130/131/136):
- Drop uq_file_folders_tenant_parent_name (tenant_id, parent_id, name)
- Add uq_file_folders_tenant_parent_scope_name_project
  (tenant_id, parent_id, scope, name, project_id)

Rationale: per-project folders + per-scope uniqueness. USER scope has no
folders (virtual "My files" root), so folder names are unique within a
(parent, scope, project) container instead of globally per parent.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_CONSTRAINT = "uq_file_folders_tenant_parent_name"
_NEW_CONSTRAINT = "uq_file_folders_tenant_parent_scope_name_project"


def upgrade() -> None:
    op.drop_constraint(_OLD_CONSTRAINT, "file_folders", type_="unique")
    op.create_unique_constraint(
        _NEW_CONSTRAINT,
        "file_folders",
        ["tenant_id", "parent_id", "scope", "name", "project_id"],
    )


def downgrade() -> None:
    op.drop_constraint(_NEW_CONSTRAINT, "file_folders", type_="unique")
    op.create_unique_constraint(
        _OLD_CONSTRAINT,
        "file_folders",
        ["tenant_id", "parent_id", "name"],
    )
