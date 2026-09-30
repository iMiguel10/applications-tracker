"""notificaciones por email

Revision ID: f58741a45d81
Revises: 5a4f9860f364
Create Date: 2026-09-30 09:03:34.962323

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f58741a45d81"
down_revision: str | Sequence[str] | None = "5a4f9860f364"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """F12 (RF-80…87): entregas de avisos por email ("nunca dos veces", A20) y las
    preferencias de aviso en `users` (RF-80, RF-81, RF-84). Los valores de los CHECK se
    congelan aquí como texto."""
    op.create_table(
        "notification_deliveries",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False),
        sa.Column(
            "channel",
            sa.String(length=20),
            server_default="email",
            nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('reminder_due', 'interview_upcoming', 'weekly_digest', "
            "'stale_application')",
            name=op.f("ck_notification_deliveries_kind"),
        ),
        sa.CheckConstraint(
            "channel IN ('email')", name=op.f("ck_notification_deliveries_channel")
        ),
        sa.CheckConstraint(
            "status IN ('claimed', 'sent', 'failed', 'unknown')",
            name=op.f("ck_notification_deliveries_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notification_deliveries_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_deliveries")),
        sa.UniqueConstraint(
            "user_id",
            "kind",
            "channel",
            "dedupe_key",
            name=op.f("uq_notification_deliveries_user_id_kind_channel_dedupe_key"),
        ),
    )
    op.create_index(
        "ix_notification_deliveries_claimed_at_claimed",
        "notification_deliveries",
        ["claimed_at"],
        unique=False,
        postgresql_where=sa.text("status = 'claimed'"),
    )
    op.add_column(
        "users",
        sa.Column(
            "notify_reminder_due",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "notify_interview",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "notify_weekly_digest",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "notify_stale",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "reminder_notice_hours",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "interview_notice_hours",
            sa.SmallInteger(),
            server_default="24",
            nullable=False,
        ),
    )
    # Autogenerate no incluye los CHECK al modificar una tabla existente.
    op.create_check_constraint(
        op.f("ck_users_interview_notice_hours_range"),
        "users",
        "interview_notice_hours BETWEEN 1 AND 168",
    )
    op.create_check_constraint(
        op.f("ck_users_reminder_notice_hours_range"),
        "users",
        "reminder_notice_hours BETWEEN 0 AND 168",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_users_reminder_notice_hours_range"), "users", type_="check"
    )
    op.drop_column("users", "reminder_notice_hours")
    op.drop_constraint(
        op.f("ck_users_interview_notice_hours_range"), "users", type_="check"
    )
    op.drop_column("users", "interview_notice_hours")
    op.drop_column("users", "notify_stale")
    op.drop_column("users", "notify_weekly_digest")
    op.drop_column("users", "notify_interview")
    op.drop_column("users", "notify_reminder_due")
    op.drop_index(
        "ix_notification_deliveries_claimed_at_claimed",
        table_name="notification_deliveries",
        postgresql_where=sa.text("status = 'claimed'"),
    )
    op.drop_table("notification_deliveries")
