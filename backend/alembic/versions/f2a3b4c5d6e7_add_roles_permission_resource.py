"""add_roles_permission_resource

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-08-06 10:00:00.000000

FEAT-016 part 2 (TODO-163): grant the new `roles` resource to the system
roles so tenant admins/managers can manage custom roles through the roles
API. admin + manager get manage/roles + view/roles; employee gets
view/roles. Deterministic system role ids reuse the seed migration
(e1f2a3b4c5d6); app code never references them (lookups go by name).

Downgrade deletes exactly the rows this migration inserted.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SYSTEM_ROLE_IDS: dict[str, uuid.UUID] = {
    "super_admin": uuid.UUID("11111111-1111-4111-8111-111111111111"),
    "admin": uuid.UUID("22222222-2222-4222-8222-222222222222"),
    "manager": uuid.UUID("33333333-3333-4333-8333-333333333333"),
    "employee": uuid.UUID("44444444-4444-4444-8444-444444444444"),
}

_ROLES_GRANTS: dict[str, list[tuple[str, str]]] = {
    "admin": [("manage", "roles"), ("view", "roles")],
    "manager": [("manage", "roles"), ("view", "roles")],
    "employee": [("view", "roles")],
}


def upgrade() -> None:
    permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("action", sa.String()),
        sa.column("resource", sa.String()),
        sa.column("granted", sa.Boolean()),
    )
    for name, grants in _ROLES_GRANTS.items():
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
                for action, resource in grants
            ],
        )


def downgrade() -> None:
    for name, grants in _ROLES_GRANTS.items():
        for action, resource in grants:
            op.execute(
                sa.text(
                    "DELETE FROM role_permissions "
                    "WHERE role_id = :role_id AND action = :action AND resource = :resource"
                ).bindparams(
                    role_id=_SYSTEM_ROLE_IDS[name],
                    action=action,
                    resource=resource,
                )
            )
