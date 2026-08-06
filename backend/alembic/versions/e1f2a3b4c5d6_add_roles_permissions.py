"""add_roles_permissions

Revision ID: e1f2a3b4c5d6
Revises: a0b1c2d3e4f5
Create Date: 2026-08-06 09:00:00.000000

FEAT-016 part 1 (TODO-161): role rows + permissions + admin_users.role_id.

NOTE: spec-requested revision id "b1c2d3e4f5a6" is already taken by
b1c2d3e4f5a6_add_service_milestone_steptemplate; this migration uses
e1f2a3b4c5d6 instead (still child of a0b1c2d3e4f5).

- roles: system built-ins (tenant_id NULL) + future tenant custom roles;
  partial unique index on name WHERE tenant_id IS NULL + unique (tenant_id, name)
- role_permissions: granted action/resource rows per role
- seeds system roles (super_admin/admin/manager/employee) and the current
  permission matrix from app/services/permissions.py (via
  app.services.roles.SYSTEM_ROLE_PERMISSIONS); super_admin carries no
  permission rows (platform access stays code-gated)
- admin_users.role_id: nullable FK, backfilled from the role enum, then
  NOT NULL (all existing rows resolve to a seeded system role)

Downgrade reverses (role_id dropped, tables dropped).
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.services.roles import SYSTEM_ROLE_PERMISSIONS

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "a0b1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Deterministic ids for seeded system roles (ids are never referenced by
# app code — lookups go by name — but fixed ids keep the seed reproducible).
_SYSTEM_ROLE_IDS: dict[str, uuid.UUID] = {
    "super_admin": uuid.UUID("11111111-1111-4111-8111-111111111111"),
    "admin": uuid.UUID("22222222-2222-4222-8222-222222222222"),
    "manager": uuid.UUID("33333333-3333-4333-8333-333333333333"),
    "employee": uuid.UUID("44444444-4444-4444-8444-444444444444"),
}


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
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
            name=op.f("fk_roles_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
    )
    op.create_index(
        "uq_roles_system_name",
        "roles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )
    op.create_unique_constraint(op.f("uq_roles_tenant_name"), "roles", ["tenant_id", "name"])

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
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
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_role_permissions_role_id_roles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_permissions")),
        sa.UniqueConstraint(
            "role_id",
            "action",
            "resource",
            name=op.f("uq_role_permissions_role_action_resource"),
        ),
    )
    op.create_index(op.f("ix_role_permissions_role_id"), "role_permissions", ["role_id"], unique=False)

    # ── Seed system roles + permissions (current matrix) ─────────────────
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("tenant_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        roles_table,
        [
            {
                "id": role_id,
                "tenant_id": None,
                "name": name,
                "description": f"System built-in role: {name}",
                "is_system": True,
            }
            for name, role_id in _SYSTEM_ROLE_IDS.items()
        ],
    )

    permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("action", sa.String()),
        sa.column("resource", sa.String()),
        sa.column("granted", sa.Boolean()),
    )
    for name, perms in SYSTEM_ROLE_PERMISSIONS.items():
        op.bulk_insert(
            permissions_table,
            [
                {
                    "id": uuid.uuid4(),
                    "role_id": _SYSTEM_ROLE_IDS[name],
                    "action": action,
                    "resource": resource,
                    "granted": True,
                }
                for action, resource in sorted(perms)
            ],
        )

    # ── admin_users.role_id (backfill from role enum, then NOT NULL) ─────
    op.add_column(
        "admin_users",
        sa.Column("role_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_admin_users_role_id_roles"),
        "admin_users",
        "roles",
        ["role_id"],
        ["id"],
    )
    op.execute(
        sa.text(
            "UPDATE admin_users SET role_id = ("
            "SELECT r.id FROM roles r "
            "WHERE r.name = lower(admin_users.role::text) AND r.tenant_id IS NULL"
            ")"
        )
    )
    op.alter_column(
        "admin_users",
        "role_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "admin_users",
        "role_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.drop_constraint(
        op.f("fk_admin_users_role_id_roles"),
        "admin_users",
        type_="foreignkey",
    )
    op.drop_column("admin_users", "role_id")

    op.drop_index(op.f("ix_role_permissions_role_id"), table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_table("roles")
