"""clave del almacen unica

Revision ID: 915848114c72
Revises: c8e717d0e256
Create Date: 2026-09-30 16:51:07.715847

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "915848114c72"
down_revision: str | Sequence[str] | None = "c8e717d0e256"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """F13 (paso 6): una clave del almacén, un documento; y el índice del barrido
    de huérfanos, que busca en lote qué claves tienen fila (ficheros §5)."""
    op.create_unique_constraint(
        op.f("uq_documents_storage_key"), "documents", ["storage_key"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_documents_storage_key"), "documents", type_="unique")
