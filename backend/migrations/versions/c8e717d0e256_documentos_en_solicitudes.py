"""documentos en solicitudes

Revision ID: c8e717d0e256
Revises: 172ae8ce6c33
Create Date: 2026-09-30 16:10:07.905427

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e717d0e256"
down_revision: str | Sequence[str] | None = "172ae8ce6c33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """F13 (RF-27, RF-28): la descripción de la oferta y el CV y la carta enviados.
    FK compuestas con user_id (documentos del mismo usuario) y NO ACTION, no
    RESTRICT: RESTRICT haría fallar el borrado de la cuenta (ver el modelo)."""
    op.add_column(
        "applications", sa.Column("job_description", sa.Text(), nullable=True)
    )
    op.add_column("applications", sa.Column("cv_document_id", sa.Uuid(), nullable=True))
    op.add_column(
        "applications", sa.Column("cover_letter_document_id", sa.Uuid(), nullable=True)
    )
    # Autogenerate no incluye los CHECK al modificar una tabla existente.
    op.create_check_constraint(
        op.f("ck_applications_job_description_length"),
        "applications",
        "char_length(job_description) <= 20000",
    )
    op.create_index(
        "ix_applications_cover_letter_document_id",
        "applications",
        ["cover_letter_document_id"],
        unique=False,
        postgresql_where=sa.text("cover_letter_document_id IS NOT NULL"),
    )
    op.create_index(
        "ix_applications_cv_document_id",
        "applications",
        ["cv_document_id"],
        unique=False,
        postgresql_where=sa.text("cv_document_id IS NOT NULL"),
    )
    op.create_foreign_key(
        op.f("fk_applications_cover_letter_document_id_documents"),
        "applications",
        "documents",
        ["cover_letter_document_id", "user_id"],
        ["id", "user_id"],
    )
    op.create_foreign_key(
        op.f("fk_applications_cv_document_id_documents"),
        "applications",
        "documents",
        ["cv_document_id", "user_id"],
        ["id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_applications_job_description_length"), "applications", type_="check"
    )
    op.drop_constraint(
        op.f("fk_applications_cv_document_id_documents"),
        "applications",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_applications_cover_letter_document_id_documents"),
        "applications",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_applications_cv_document_id",
        table_name="applications",
        postgresql_where=sa.text("cv_document_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_applications_cover_letter_document_id",
        table_name="applications",
        postgresql_where=sa.text("cover_letter_document_id IS NOT NULL"),
    )
    op.drop_column("applications", "cover_letter_document_id")
    op.drop_column("applications", "cv_document_id")
    op.drop_column("applications", "job_description")
