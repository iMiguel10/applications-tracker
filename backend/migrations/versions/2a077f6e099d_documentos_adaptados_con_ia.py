"""documentos adaptados con IA

Revision ID: 2a077f6e099d
Revises: 7aad505b5fb2
Create Date: 2026-10-07 17:54:22.147499

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a077f6e099d"
down_revision: str | Sequence[str] | None = "7aad505b5fb2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """F15: el documento adaptado con IA apunta a la propuesta de la que sale."""
    op.add_column("documents", sa.Column("ai_proposal_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_documents_ai_proposal_id_ai_proposals"),
        "documents",
        "ai_proposals",
        ["ai_proposal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_documents_ai_proposal_id",
        "documents",
        ["ai_proposal_id"],
        unique=False,
        postgresql_where=sa.text("ai_proposal_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_documents_ai_proposal_id",
        table_name="documents",
        postgresql_where=sa.text("ai_proposal_id IS NOT NULL"),
    )
    op.drop_constraint(
        op.f("fk_documents_ai_proposal_id_ai_proposals"),
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "ai_proposal_id")
