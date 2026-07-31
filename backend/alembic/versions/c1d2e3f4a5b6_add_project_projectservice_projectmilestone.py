"""add_project_projectservice_projectmilestone

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-07-31 22:00:00.000000

Adds project management core (FEAT-007, TODO-062/064/068):
- projects: tenant-scoped work item for a client (status, start_date, owner)
- project_services: join entity (project + service) with price snapshot
- project_milestones: instantiated copies of MilestoneStepTemplate per
  ProjectService, with status / planned / actual / assignee fields
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "ON_HOLD",
                "COMPLETED",
                "CANCELLED",
                name="projectstatus",
            ),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
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
            ["client_id"], ["clients.id"], name=op.f("fk_projects_client_id_clients")
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["admin_users.id"],
            name=op.f("fk_projects_owner_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name=op.f("fk_projects_tenant_id_tenants")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_index(op.f("ix_projects_tenant_id"), "projects", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_projects_client_id"), "projects", ["client_id"], unique=False)
    op.create_index("ix_projects_tenant_status", "projects", ["tenant_id", "status"], unique=False)

    op.create_table(
        "project_services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "CANCELLED", name="projectservicestatus"),
            nullable=False,
        ),
        sa.Column("price_at_attachment", sa.Numeric(precision=12, scale=2), nullable=True),
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
            name=op.f("fk_project_services_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_project_services_service_id_services"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_services")),
        sa.UniqueConstraint(
            "project_id",
            "service_id",
            name="uq_project_services_project_id_service_id",
        ),
    )
    op.create_index(
        op.f("ix_project_services_project_id"),
        "project_services",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_services_service_id"),
        "project_services",
        ["service_id"],
        unique=False,
    )

    op.create_table(
        "project_milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_service_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                "BLOCKED",
                name="milestonestatus",
            ),
            nullable=False,
        ),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
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
            ["assignee_id"],
            ["admin_users.id"],
            name=op.f("fk_project_milestones_assignee_id_admin_users"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_milestones_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_service_id"],
            ["project_services.id"],
            name=op.f("fk_project_milestones_project_service_id_project_services"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_project_milestones_service_id_services"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_milestones")),
    )
    op.create_index(
        op.f("ix_project_milestones_project_id"),
        "project_milestones",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_project_milestones_project_service_id"),
        "project_milestones",
        ["project_service_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_milestones_project_seq",
        "project_milestones",
        ["project_id", "sequence_order"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_milestones_project_seq", table_name="project_milestones")
    op.drop_index(
        op.f("ix_project_milestones_project_service_id"),
        table_name="project_milestones",
    )
    op.drop_index(
        op.f("ix_project_milestones_project_id"), table_name="project_milestones"
    )
    op.drop_table("project_milestones")
    sa.Enum(name="milestonestatus").drop(op.get_bind(), checkfirst=True)
    op.drop_index(
        op.f("ix_project_services_service_id"), table_name="project_services"
    )
    op.drop_index(
        op.f("ix_project_services_project_id"), table_name="project_services"
    )
    op.drop_table("project_services")
    sa.Enum(name="projectservicestatus").drop(op.get_bind(), checkfirst=True)
    op.drop_index("ix_projects_tenant_status", table_name="projects")
    op.drop_index(op.f("ix_projects_client_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_tenant_id"), table_name="projects")
    op.drop_table("projects")
    sa.Enum(name="projectstatus").drop(op.get_bind(), checkfirst=True)
