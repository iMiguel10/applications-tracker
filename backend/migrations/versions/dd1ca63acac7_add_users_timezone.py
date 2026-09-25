"""add users timezone

Revision ID: dd1ca63acac7
Revises: 458290ff94e6
Create Date: 2026-09-25 10:17:56.953556

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dd1ca63acac7"
down_revision: str | Sequence[str] | None = "458290ff94e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """F11 (RF-07, A39): zona IANA del usuario. Admite nulos (las cuentas existentes
    la reciben del frontend al volver a entrar) y sin CHECK: la lista de zonas
    cambia con tzdata y la valida la aplicación."""
    op.add_column("users", sa.Column("timezone", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "timezone")
