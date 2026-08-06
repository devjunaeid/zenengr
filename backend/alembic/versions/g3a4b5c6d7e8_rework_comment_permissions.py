"""rework_comment_permissions

Revision ID: g3a4b5c6d7e8
Revises: f2a3b4c5d6e7
Create Date: 2026-08-06 11:00:00.000000

FEAT-016/010 refinement (product decision): replace the legacy comment
permissions `manage/comments` and `manage_assigned/comments` with
`post/comments` ("Can comment") and `edit/comments` ("Edit comments").

Mapping (applies to system AND custom roles):
- Roles that had manage/comments  -> post/comments + edit/comments
- Roles that had manage_assigned/comments only -> post/comments

Upgrade: capture affected roles per legacy key, delete the legacy rows,
insert the replacement rows.

Downgrade (approximate reverse): delete the new rows; roles with
post+edit/comments get manage/comments back, post-only roles get
manage_assigned/comments back.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g3a4b5c6d7e8"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INSERT_PERMISSION = sa.text(
    "INSERT INTO role_permissions (id, role_id, action, resource, granted, created_at, updated_at) "
    "VALUES (:id, :role_id, :action, :resource, TRUE, now(), now())"
)


def _insert(session, *, role_id: uuid.UUID, action: str, resource: str) -> None:
    session.execute(
        _INSERT_PERMISSION.bindparams(
            id=uuid.uuid4(),
            role_id=role_id,
            action=action,
            resource=resource,
        )
    )


def upgrade() -> None:
    session = op.get_bind()

    manage_role_ids = set(
        session.execute(
            sa.text(
                "SELECT DISTINCT role_id FROM role_permissions "
                "WHERE action = 'manage' AND resource = 'comments' AND granted = TRUE"
            )
        ).scalars()
    )
    assigned_role_ids = set(
        session.execute(
            sa.text(
                "SELECT DISTINCT role_id FROM role_permissions "
                "WHERE action = 'manage_assigned' AND resource = 'comments' AND granted = TRUE"
            )
        ).scalars()
    )

    # Remove the legacy keys entirely (all roles).
    op.execute(
        sa.text(
            "DELETE FROM role_permissions "
            "WHERE (action = 'manage' AND resource = 'comments') "
            "OR (action = 'manage_assigned' AND resource = 'comments')"
        )
    )

    # manage/comments roles -> post + edit
    for role_id in manage_role_ids:
        _insert(session, role_id=role_id, action="post", resource="comments")
        _insert(session, role_id=role_id, action="edit", resource="comments")

    # manage_assigned/comments-only roles -> post
    for role_id in assigned_role_ids - manage_role_ids:
        _insert(session, role_id=role_id, action="post", resource="comments")


def downgrade() -> None:
    session = op.get_bind()

    edit_role_ids = set(
        session.execute(
            sa.text(
                "SELECT DISTINCT role_id FROM role_permissions "
                "WHERE action = 'edit' AND resource = 'comments' AND granted = TRUE"
            )
        ).scalars()
    )
    post_role_ids = set(
        session.execute(
            sa.text(
                "SELECT DISTINCT role_id FROM role_permissions "
                "WHERE action = 'post' AND resource = 'comments' AND granted = TRUE"
            )
        ).scalars()
    )

    # Delete the new rows.
    op.execute(
        sa.text(
            "DELETE FROM role_permissions "
            "WHERE (action = 'post' AND resource = 'comments') "
            "OR (action = 'edit' AND resource = 'comments')"
        )
    )

    # post+edit roles -> manage (approximate reverse of the mapping)
    for role_id in edit_role_ids:
        _insert(session, role_id=role_id, action="manage", resource="comments")

    # post-only roles -> manage_assigned
    for role_id in post_role_ids - edit_role_ids:
        _insert(session, role_id=role_id, action="manage_assigned", resource="comments")
