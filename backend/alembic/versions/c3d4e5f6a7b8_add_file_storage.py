"""add_file_storage

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-05 09:00:00.000000

FEAT-012 (TODO-123/124/125/137):
- filescope enum (USER/TENANT/PROJECT)
- file_folders: tenant-scoped folder tree, root folders provisioned lazily
- file_assets: uploaded file records (storage keys, content hash, size)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    filescope = postgresql.ENUM("USER", "TENANT", "PROJECT", name="filescope", create_type=False)
    filescope.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "file_folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", filescope, nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_type", sa.String(length=20), nullable=False),
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
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_file_folders_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["file_folders.id"],
            name=op.f("fk_file_folders_parent_id_file_folders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_file_folders_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_file_folders")),
        sa.UniqueConstraint(
            "tenant_id",
            "parent_id",
            "name",
            name="uq_file_folders_tenant_parent_name",
        ),
    )
    op.create_index(op.f("ix_file_folders_tenant_id"), "file_folders", ["tenant_id"], unique=False)

    op.create_table(
        "file_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=True),
        sa.Column("scope", filescope, nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
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
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_file_assets_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["file_folders.id"],
            name=op.f("fk_file_assets_folder_id_file_folders"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_file_assets_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_file_assets")),
        sa.UniqueConstraint("storage_key", name="uq_file_assets_storage_key"),
    )
    op.create_index(op.f("ix_file_assets_tenant_id"), "file_assets", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_file_assets_folder_id"), "file_assets", ["folder_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_file_assets_folder_id"), table_name="file_assets")
    op.drop_index(op.f("ix_file_assets_tenant_id"), table_name="file_assets")
    op.drop_table("file_assets")

    op.drop_index(op.f("ix_file_folders_tenant_id"), table_name="file_folders")
    op.drop_table("file_folders")

    sa.Enum(name="filescope").drop(op.get_bind(), checkfirst=True)
