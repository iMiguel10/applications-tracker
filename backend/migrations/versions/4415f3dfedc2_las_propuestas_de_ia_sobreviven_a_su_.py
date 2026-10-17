"""las propuestas de ia sobreviven a su solicitud

Revision ID: 4415f3dfedc2
Revises: f479ab60e412
Create Date: 2026-10-17 16:22:00.284587

Encontrado en el QA de F15: `ai_proposals` es el registro de consumo de la cuota
gratuita, y con `ON DELETE CASCADE` borrar la solicitud borraba sus propuestas y
devolvía el uso. Ahora solo se vacía `application_id` (`SET NULL` con lista de
columnas, Postgres 15+: `user_id` queda intacto y la propuesta sigue contando).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4415f3dfedc2"
down_revision: str | Sequence[str] | None = "f479ab60e412"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK = "fk_ai_proposals_application_id_applications"


def _foreign_key(ondelete: str) -> None:
    op.create_foreign_key(
        op.f(_FK),
        "ai_proposals",
        "applications",
        ["application_id", "user_id"],
        ["id", "user_id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    op.drop_constraint(op.f(_FK), "ai_proposals", type_="foreignkey")
    op.alter_column("ai_proposals", "application_id", nullable=True)
    _foreign_key("SET NULL (application_id)")


def downgrade() -> None:
    op.drop_constraint(op.f(_FK), "ai_proposals", type_="foreignkey")
    # Las de solicitudes borradas no caben en la columna obligatoria: con la regla
    # anterior se habrían borrado al borrar la solicitud.
    op.execute("DELETE FROM ai_proposals WHERE application_id IS NULL")
    op.alter_column("ai_proposals", "application_id", nullable=False)
    _foreign_key("CASCADE")
