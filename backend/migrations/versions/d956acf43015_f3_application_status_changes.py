"""f3 application status changes

Revision ID: d956acf43015
Revises: d139e1dd5b00
Create Date: 2026-09-23 09:00:57.823882

Escrita a mano: autogenerate no genera columnas `GENERATED ALWAYS AS IDENTITY` (seq,
decisión 0004) con la sintaxis correcta, y tampoco habría generado el backfill.

Tras crear la tabla, inserta el cambio inicial de cada solicitud ya existente,
tomando su propio `created_at` como `changed_at` y `created_at` del cambio: es la
mejor aproximación disponible a "cuándo se registró", y restaura la invariante 4
("toda solicitud tiene al menos un cambio en su historial"), que hasta ahora no
podía cumplirse porque esta tabla no existía (ver CLAUDE.md, estado F2).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d956acf43015"
down_revision: str | Sequence[str] | None = "d139e1dd5b00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Congelado aquí a propósito (igual que en la migración de F2): una migración
# describe el esquema de SU momento y no debe cambiar si domain/ cambia mañana.
STATUSES = (
    "'saved', 'applied', 'screening', 'interviewing', 'offer', "
    "'accepted', 'rejected', 'withdrawn'"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "application_status_changes",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column(
            "seq",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"from_status IN ({STATUSES})",
            name=op.f("ck_application_status_changes_from_status"),
        ),
        sa.CheckConstraint(
            f"to_status IN ({STATUSES})",
            name=op.f("ck_application_status_changes_to_status"),
        ),
        sa.CheckConstraint(
            "char_length(note) <= 5000",
            name=op.f("ck_application_status_changes_note_length"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_status_changes_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_status_changes")),
        sa.UniqueConstraint("seq", name=op.f("uq_application_status_changes_seq")),
    )
    op.create_index(
        "ix_application_status_changes_application_id_seq",
        "application_status_changes",
        ["application_id", sa.literal_column("seq DESC")],
    )

    # Backfill: el cambio inicial de cada solicitud existente (ver docstring).
    op.execute(
        """
        INSERT INTO application_status_changes
            (application_id, from_status, to_status, changed_at, created_at)
        SELECT id, NULL, status, created_at, created_at
        FROM applications
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_application_status_changes_application_id_seq",
        table_name="application_status_changes",
    )
    op.drop_table("application_status_changes")
