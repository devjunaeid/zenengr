"""add_notification_channels_and_model

Revision ID: h4a5b6c7d8e9
Revises: g3a4b5c6d7e8
Create Date: 2026-08-07 09:00:00.000000

FEAT-017 part 1 (TODO-168/169):
- notificationeventtype: add REFUND_RECORDED, ADVANCE_APPLIED, PROJECT_CREATED
- notificationchannel enum (EMAIL / INAPP); notification_preferences gains a
  `channel` column; unique constraint extended to (user_id, user_type,
  event_type, channel)
- notifications table: persisted in-app notification rows (model only; the
  notification service/WS ships in the next batch)

Enum values are stored as the SQLAlchemy member NAMES (existing convention,
e.g. NEW_COMMENT) — the ORM persists names, not the lowercase StrEnum values.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h4a5b6c7d8e9"
down_revision: str | None = "g3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_EVENT_VALUES = ("REFUND_RECORDED", "ADVANCE_APPLIED", "PROJECT_CREATED")


def _create_enum_if_not_exists(name: str, values: list[str]) -> None:
    """Create PG enum type idempotently (PG16 compatible DO block)."""
    vals = ", ".join(f"'{v}'" for v in values)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                CREATE TYPE {name} AS ENUM ({vals});
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    # 1. Extend notificationeventtype. PG12+ allows ADD VALUE inside a
    # migration transaction as long as the new values are not used in the
    # same transaction (they are not).
    for value in _NEW_EVENT_VALUES:
        op.execute(f"ALTER TYPE notificationeventtype ADD VALUE IF NOT EXISTS '{value}'")

    # 2. notification_preferences.channel
    _create_enum_if_not_exists("notificationchannel", ["EMAIL", "INAPP"])
    notificationchannel = postgresql.ENUM(
        "EMAIL", "INAPP", name="notificationchannel", create_type=False
    )
    notificationchannel._create_events = False  # noqa: SLF001

    notificationeventtype = postgresql.ENUM(
        "NEW_COMMENT",
        "INVOICE_ISSUED",
        "PAYMENT_RECEIVED",
        "MILESTONE_COMPLETED",
        "REFUND_RECORDED",
        "ADVANCE_APPLIED",
        "PROJECT_CREATED",
        name="notificationeventtype",
        create_type=False,
    )
    notificationeventtype._create_events = False  # noqa: SLF001

    op.add_column(
        "notification_preferences",
        sa.Column(
            "channel",
            notificationchannel,
            server_default=sa.text("'EMAIL'"),
            nullable=False,
        ),
    )
    op.drop_constraint(
        "uq_notification_preferences_user_event",
        "notification_preferences",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_notification_preferences_user_event_channel"),
        "notification_preferences",
        ["user_id", "user_type", "event_type", "channel"],
    )

    # 3. notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_type", sa.String(length=20), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "event_type",
            notificationeventtype,
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), server_default="", nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
            name=op.f("fk_notifications_tenant_id_tenants"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        op.f("ix_notifications_user_created"),
        "notifications",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_user_read"),
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_user_read"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_created"), table_name="notifications")
    op.drop_table("notifications")

    op.drop_constraint(
        op.f("uq_notification_preferences_user_event_channel"),
        "notification_preferences",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_notification_preferences_user_event",
        "notification_preferences",
        ["user_id", "user_type", "event_type"],
    )
    op.drop_column("notification_preferences", "channel")
    op.execute("DROP TYPE IF EXISTS notificationchannel CASCADE")

    # PG limitation: ALTER TYPE ... DROP VALUE is unsupported, so the three
    # new notificationeventtype values (REFUND_RECORDED, ADVANCE_APPLIED,
    # PROJECT_CREATED) REMAIN in the enum type after downgrade. They are
    # harmless extra values; the ORM model no longer emits them. Recreating
    # the type to remove them is not done here to avoid a table rewrite.
