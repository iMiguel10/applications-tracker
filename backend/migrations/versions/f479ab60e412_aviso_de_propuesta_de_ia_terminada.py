"""aviso de propuesta de ia terminada

Revision ID: f479ab60e412
Revises: 4dc4b759ec3e
Create Date: 2026-10-17 10:10:00.886117

F15 paso 6 (RF-157, decisión 0021): el aviso por email al terminar una propuesta.
`users.notify_ai_proposal` (apagado), `ai_proposals.finished_at` (las anteriores
quedan sin él y nunca se avisan) y el tipo nuevo en el CHECK de
`notification_deliveries.kind`, que autogenerate no detecta.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f479ab60e412"
down_revision: str | Sequence[str] | None = "4dc4b759ec3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Los valores, congelados como texto (CLAUDE.md, trampas).
_KINDS_BEFORE = (
    "'reminder_due', 'interview_upcoming', 'weekly_digest', 'stale_application'"
)
_KINDS_AFTER = f"{_KINDS_BEFORE}, 'ai_proposal_finished'"
_KIND_CHECK = "ck_notification_deliveries_kind"


def upgrade() -> None:
    op.add_column(
        "ai_proposals",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    # El barrido de RF-157 busca las terminadas en la última hora.
    op.create_index(
        "ix_ai_proposals_finished_at",
        "ai_proposals",
        ["finished_at"],
        postgresql_where=sa.text("finished_at IS NOT NULL"),
    )
    op.add_column(
        "users",
        sa.Column(
            "notify_ai_proposal",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.drop_constraint(op.f(_KIND_CHECK), "notification_deliveries", type_="check")
    op.create_check_constraint(
        op.f(_KIND_CHECK), "notification_deliveries", f"kind IN ({_KINDS_AFTER})"
    )


def downgrade() -> None:
    # Sin el tipo, sus entregas no cabrían en el CHECK anterior.
    op.execute(
        "DELETE FROM notification_deliveries WHERE kind = 'ai_proposal_finished'"
    )
    op.drop_constraint(op.f(_KIND_CHECK), "notification_deliveries", type_="check")
    op.create_check_constraint(
        op.f(_KIND_CHECK), "notification_deliveries", f"kind IN ({_KINDS_BEFORE})"
    )
    op.drop_column("users", "notify_ai_proposal")
    op.drop_index("ix_ai_proposals_finished_at", table_name="ai_proposals")
    op.drop_column("ai_proposals", "finished_at")
