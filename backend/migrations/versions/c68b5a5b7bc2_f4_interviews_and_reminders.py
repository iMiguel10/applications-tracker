"""f4 interviews and reminders

Revision ID: c68b5a5b7bc2
Revises: d956acf43015
Create Date: 2026-09-23 10:16:16.526861

Escrita a mano: autogenerate no incluiría los CHECK (solo los detecta al crear una
tabla que ya existe, no aplica aquí, pero se completan igual a mano por consistencia
con el resto de migraciones) ni el índice parcial de `reminders`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c68b5a5b7bc2"
down_revision: str | Sequence[str] | None = "d956acf43015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Congelados aquí a propósito (igual que en las migraciones de F2 y F3): una
# migración describe el esquema de SU momento y no debe cambiar si domain/ cambia.
INTERVIEW_TYPES = "'screening', 'technical', 'hr', 'cultural', 'final', 'other'"
INTERVIEW_FORMATS = "'online', 'onsite', 'phone'"
INTERVIEW_OUTCOMES = "'pending', 'passed', 'failed', 'cancelled'"
REMINDER_CHANNELS = "'in_app'"
REMINDER_STATUSES = "'pending', 'done', 'dismissed'"


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "interviews",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("interviewers", sa.String(length=500), nullable=True),
        sa.Column("interview_type", sa.String(length=20), nullable=True),
        sa.Column("format", sa.String(length=20), nullable=True),
        sa.Column(
            "outcome", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            f"interview_type IN ({INTERVIEW_TYPES})",
            name=op.f("ck_interviews_interview_type"),
        ),
        sa.CheckConstraint(
            f"format IN ({INTERVIEW_FORMATS})", name=op.f("ck_interviews_format")
        ),
        sa.CheckConstraint(
            f"outcome IN ({INTERVIEW_OUTCOMES})", name=op.f("ck_interviews_outcome")
        ),
        sa.CheckConstraint(
            "char_length(notes) <= 5000", name=op.f("ck_interviews_notes_length")
        ),
        sa.CheckConstraint(
            "duration_minutes > 0",
            name=op.f("ck_interviews_duration_minutes_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_interviews_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviews")),
    )
    op.create_index(
        "ix_interviews_application_id_scheduled_at",
        "interviews",
        ["application_id", "scheduled_at"],
    )

    op.create_table(
        "reminders",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "channel", sa.String(length=20), server_default="in_app", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        *_timestamps(),
        sa.CheckConstraint(
            f"channel IN ({REMINDER_CHANNELS})", name=op.f("ck_reminders_channel")
        ),
        sa.CheckConstraint(
            f"status IN ({REMINDER_STATUSES})", name=op.f("ck_reminders_status")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_reminders_user_id_users"),
            ondelete="CASCADE",
        ),
        # Compuesta y opcional (A9): si application_id no es NULL, tiene que ser una
        # solicitud del MISMO usuario. MATCH SIMPLE (por defecto) no comprueba la FK
        # cuando application_id es NULL, así que un recordatorio sin solicitud es válido.
        sa.ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name=op.f("fk_reminders_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminders")),
    )
    op.create_index(
        "ix_reminders_user_id_due_at_pending",
        "reminders",
        ["user_id", "due_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_reminders_user_id_due_at_pending", table_name="reminders")
    op.drop_table("reminders")
    op.drop_index("ix_interviews_application_id_scheduled_at", table_name="interviews")
    op.drop_table("interviews")
