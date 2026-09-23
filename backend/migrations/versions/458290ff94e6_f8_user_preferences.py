"""f8 user preferences

Revision ID: 458290ff94e6
Revises: ccd567a4b214
Create Date: 2026-09-23 15:20:59.629253

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "458290ff94e6"
down_revision: str | Sequence[str] | None = "ccd567a4b214"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("language", sa.String(length=2), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "stale_after_days", sa.SmallInteger(), server_default="14", nullable=False
        ),
    )
    # autogenerate no incluye los CHECK al modificar una tabla existente (trampa
    # conocida): se añaden a mano.
    op.create_check_constraint(
        op.f("ck_users_language"), "users", "language IN ('es', 'en')"
    )
    op.create_check_constraint(
        op.f("ck_users_stale_after_days_range"),
        "users",
        "stale_after_days BETWEEN 1 AND 90",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_users_stale_after_days_range"), "users", type_="check")
    op.drop_constraint(op.f("ck_users_language"), "users", type_="check")
    op.drop_column("users", "stale_after_days")
    op.drop_column("users", "language")
