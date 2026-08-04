"""add_comments

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-08-03 12:00:00.000000

Adds project comments (FEAT-010, TODO-100/103/104/106/107):
- comments: project-scoped, polymorphic author (admin_users.id or
  client_users.id), author_type enum + author_name snapshot, shared vs
  internal visibility flag
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column(
            "author_type",
            sa.Enum(
                "TENANT_ADMIN",
                "TENANT_MANAGER",
                "TENANT_EMPLOYEE",
                "CLIENT_USER",
                name="commentauthortype",
            ),
            nullable=False,
        ),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False),
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
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_comments_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(op.f("ix_comments_project_id"), "comments", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_comments_project_id"), table_name="comments")
    op.drop_table("comments")
    sa.Enum(name="commentauthortype").drop(op.get_bind(), checkfirst=True)
