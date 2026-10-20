"""aceptacion de los textos legales

Revision ID: f61fe20856a5
Revises: 4415f3dfedc2
Create Date: 2026-10-20 14:49:27.193920

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f61fe20856a5"
down_revision: str | Sequence[str] | None = "4415f3dfedc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Qué versión de los textos legales aceptó cada cuenta y cuándo (issue #3).
    Las dos a la vez o ninguna: las cuentas que ya existen empiezan sin aceptar."""
    op.add_column(
        "users", sa.Column("legal_version", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("legal_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Autogenerate no incluye los CHECK al modificar una tabla existente.
    op.create_check_constraint(
        op.f("ck_users_legal_acceptance_complete"),
        "users",
        "(legal_version IS NULL) = (legal_accepted_at IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_users_legal_acceptance_complete"), "users", type_="check"
    )
    op.drop_column("users", "legal_accepted_at")
    op.drop_column("users", "legal_version")
