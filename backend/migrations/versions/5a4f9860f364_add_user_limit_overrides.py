"""add user limit overrides

Revision ID: 5a4f9860f364
Revises: dd1ca63acac7
Create Date: 2026-09-25 10:35:27.566759

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a4f9860f364"
down_revision: str | Sequence[str] | None = "dd1ca63acac7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """F11 (RF-143): excepciones de límites por usuario. Los valores del CHECK se
    congelan aquí como texto: si LimitKey cambia, hace falta otra migración."""
    op.create_table(
        "user_limit_overrides",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("limit_key", sa.String(length=40), nullable=False),
        # NULL = sin límite, solo donde el CHECK de abajo lo permite.
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "limit_key IN ('applications', 'companies', 'reminders')",
            name=op.f("ck_user_limit_overrides_limit_key"),
        ),
        sa.CheckConstraint(
            "value >= 0", name=op.f("ck_user_limit_overrides_value_not_negative")
        ),
        # Almacenamiento e IA (F13, F15) tendrán límite siempre: una clave nueva
        # queda fuera de esta lista y no puede guardarse como "sin límite".
        sa.CheckConstraint(
            "value IS NOT NULL OR limit_key IN "
            "('applications', 'companies', 'reminders')",
            name=op.f("ck_user_limit_overrides_unlimited_only_where_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_limit_overrides_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "user_id", "limit_key", name=op.f("pk_user_limit_overrides")
        ),
    )


def downgrade() -> None:
    op.drop_table("user_limit_overrides")
