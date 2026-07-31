"""add_service_milestone_steptemplate

Revision ID: b1c2d3e4f5a6
Revises: 81cfc015e65d
Create Date: 2026-07-31 23:00:00.000000

Adds service catalog (FEAT-006, TODO-056):
- services: tenant-scoped catalog item (name, description, default_price, is_active)
- milestone_step_templates: ordered step templates per service (FK CASCADE on delete)
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "81cfc015e65d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("default_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
            ["tenant_id"], ["tenants.id"], name=op.f("fk_services_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_services")),
    )
    op.create_index(op.f("ix_services_tenant_id"), "services", ["tenant_id"], unique=False)

    op.create_table(
        "milestone_step_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("expected_duration_days", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
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
            ["service_id"],
            ["services.id"],
            name=op.f("fk_milestone_step_templates_service_id_services"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_milestone_step_templates")),
    )
    op.create_index(
        op.f("ix_milestone_step_templates_service_id"),
        "milestone_step_templates",
        ["service_id"],
        unique=False,
    )
    op.create_index(
        "ix_milestone_step_templates_service_seq",
        "milestone_step_templates",
        ["service_id", "sequence_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_milestone_step_templates_service_seq", table_name="milestone_step_templates")
    op.drop_index(
        op.f("ix_milestone_step_templates_service_id"), table_name="milestone_step_templates"
    )
    op.drop_table("milestone_step_templates")
    op.drop_index(op.f("ix_services_tenant_id"), table_name="services")
    op.drop_table("services")
