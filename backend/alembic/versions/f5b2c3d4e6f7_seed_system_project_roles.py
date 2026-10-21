"""seed_system_project_roles

Revision ID: f5b2c3d4e6f7
Revises: e4a1b2c3d4e5
Create Date: 2026-10-21 20:15:00.000000
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5b2c3d4e6f7'
down_revision: Union[str, None] = 'e4a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_PROJECT_ROLES = [
    {
        "id": uuid.UUID("55555555-5555-4555-8555-555555555555"),
        "name": "lead",
        "description": "Project lead with full management rights on the project",
        "role_type": "project",
        "is_system": True,
        "permissions": [
            ("view", "project_overview"),
            ("edit", "project_overview"),
            ("view", "milestones"),
            ("manage", "milestones"),
            ("view", "services"),
            ("manage", "services"),
            ("view", "invoices"),
            ("manage", "invoices"),
            ("view", "purchases"),
            ("create", "purchases"),
            ("manage", "purchases"),
            ("view", "ledger"),
            ("manage", "ledger"),
            ("view", "files"),
            ("manage", "files"),
            ("view", "comments"),
            ("post", "comments"),
            ("edit", "comments"),
            ("delete", "comments"),
            ("view", "team"),
            ("manage", "team"),
        ],
    },
    {
        "id": uuid.UUID("66666666-6666-4666-8666-666666666666"),
        "name": "contributor",
        "description": "Project contributor managing milestones and files",
        "role_type": "project",
        "is_system": True,
        "permissions": [
            ("view", "project_overview"),
            ("view", "milestones"),
            ("manage", "milestones"),
            ("view", "services"),
            ("view", "files"),
            ("manage", "files"),
            ("view", "purchases"),
            ("create", "purchases"),
            ("view", "comments"),
            ("post", "comments"),
            ("edit", "comments"),
            ("view", "team"),
        ],
    },
    {
        "id": uuid.UUID("77777777-7777-4777-8777-777777777777"),
        "name": "finance",
        "description": "Project finance specialist managing invoices and purchases",
        "role_type": "project",
        "is_system": True,
        "permissions": [
            ("view", "project_overview"),
            ("view", "invoices"),
            ("manage", "invoices"),
            ("view", "purchases"),
            ("create", "purchases"),
            ("manage", "purchases"),
            ("view", "ledger"),
            ("manage", "ledger"),
            ("view", "milestones"),
            ("view", "services"),
            ("view", "files"),
            ("view", "comments"),
            ("post", "comments"),
            ("view", "team"),
        ],
    },
    {
        "id": uuid.UUID("88888888-8888-4888-8888-888888888888"),
        "name": "viewer",
        "description": "Read-only access to project details and modules",
        "role_type": "project",
        "is_system": True,
        "permissions": [
            ("view", "project_overview"),
            ("view", "milestones"),
            ("view", "services"),
            ("view", "invoices"),
            ("view", "purchases"),
            ("view", "ledger"),
            ("view", "files"),
            ("view", "comments"),
            ("view", "team"),
        ],
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    roles_table = sa.table(
        'roles',
        sa.column('id', sa.Uuid),
        sa.column('tenant_id', sa.Uuid),
        sa.column('name', sa.String),
        sa.column('description', sa.String),
        sa.column('role_type', sa.String),
        sa.column('is_system', sa.Boolean),
    )

    role_permissions_table = sa.table(
        'role_permissions',
        sa.column('id', sa.Uuid),
        sa.column('role_id', sa.Uuid),
        sa.column('action', sa.String),
        sa.column('resource', sa.String),
        sa.column('granted', sa.Boolean),
    )

    for r_data in SYSTEM_PROJECT_ROLES:
        role_id = r_data["id"]
        # Check if role exists
        existing_role = conn.execute(
            sa.text("SELECT id FROM roles WHERE id = :id OR (tenant_id IS NULL AND name = :name AND role_type = 'project')"),
            {"id": str(role_id), "name": r_data["name"]},
        ).fetchone()

        if existing_role is None:
            conn.execute(
                roles_table.insert().values(
                    id=role_id,
                    tenant_id=None,
                    name=r_data["name"],
                    description=r_data["description"],
                    role_type=r_data["role_type"],
                    is_system=True,
                )
            )
            actual_role_id = role_id
        else:
            actual_role_id = existing_role[0]

        # Insert permissions
        for action, resource in r_data["permissions"]:
            existing_perm = conn.execute(
                sa.text(
                    "SELECT id FROM role_permissions WHERE role_id = :role_id AND action = :action AND resource = :resource"
                ),
                {"role_id": str(actual_role_id), "action": action, "resource": resource},
            ).fetchone()

            if existing_perm is None:
                conn.execute(
                    role_permissions_table.insert().values(
                        id=uuid.uuid4(),
                        role_id=actual_role_id,
                        action=action,
                        resource=resource,
                        granted=True,
                    )
                )


def downgrade() -> None:
    conn = op.get_bind()
    role_ids = [str(r["id"]) for r in SYSTEM_PROJECT_ROLES]
    conn.execute(
        sa.text("DELETE FROM role_permissions WHERE role_id IN ('55555555-5555-4555-8555-555555555555', '66666666-6666-4666-8666-666666666666', '77777777-7777-4777-8777-777777777777', '88888888-8888-4888-8888-888888888888')")
    )
    conn.execute(
        sa.text("DELETE FROM roles WHERE id IN ('55555555-5555-4555-8555-555555555555', '66666666-6666-4666-8666-666666666666', '77777777-7777-4777-8777-777777777777', '88888888-8888-4888-8888-888888888888')")
    )
