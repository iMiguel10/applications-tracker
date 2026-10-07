"""propuestas de IA y consentimientos

Revision ID: 7aad505b5fb2
Revises: 9ee51b6bc414
Create Date: 2026-10-07 17:26:04.641485

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7aad505b5fb2"
down_revision: str | Sequence[str] | None = "9ee51b6bc414"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Valores congelados como texto: si LimitKey cambia, hace falta otra migración. Los
# usos de IA no admiten "sin límite" (cuestan dinero, F11), así que la lista de
# los que lo admiten no cambia.
_OLD_KEYS = "'applications', 'companies', 'reminders', 'documents', 'storage_bytes'"
_NEW_KEYS = _OLD_KEYS + ", 'ai_cv_proposals', 'ai_cover_letter_proposals'"


def _replace_limit_key_check(keys: str) -> None:
    op.drop_constraint(
        op.f("ck_user_limit_overrides_limit_key"), "user_limit_overrides"
    )
    op.create_check_constraint(
        op.f("ck_user_limit_overrides_limit_key"),
        "user_limit_overrides",
        f"limit_key IN ({keys})",
    )


def upgrade() -> None:
    """F15: cada uso de la IA (registro de consumo), los consentimientos por
    proveedor y los dos límites de usos gratuitos (decisión 0017)."""
    op.create_table(
        "ai_consents",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("text_version", sa.Integer(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "provider IN ('anthropic', 'openai', 'groq')",
            name=op.f("ck_ai_consents_provider"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_consents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_consents")),
        sa.UniqueConstraint(
            "user_id", "provider", name=op.f("uq_ai_consents_user_id_provider")
        ),
    )
    op.create_table(
        "ai_proposals",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("key_source", sa.String(length=10), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=30), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False),
        sa.Column(
            "billable", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "input_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "output_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "cost_micros", sa.BigInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "proposal",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(status = 'succeeded') = (proposal IS NOT NULL)",
            name=op.f("ck_ai_proposals_proposal_only_when_succeeded"),
        ),
        sa.CheckConstraint(
            "(status IN ('invalid', 'rejected', 'failed')) = (error_code IS NOT NULL)",
            name=op.f("ck_ai_proposals_error_code_only_when_unsuccessful"),
        ),
        sa.CheckConstraint(
            "error_code IN ('ai_provider_auth', 'ai_provider_quota', 'ai_provider_unavailable', 'ai_provider_rejected', 'ai_response_invalid', 'ai_response_refused', 'ai_offer_insufficient', 'profile_incomplete', 'ai_interrupted')",
            name=op.f("ck_ai_proposals_error_code"),
        ),
        sa.CheckConstraint(
            "key_source IN ('platform', 'user')",
            name=op.f("ck_ai_proposals_key_source"),
        ),
        sa.CheckConstraint(
            "kind IN ('cv', 'cover_letter')", name=op.f("ck_ai_proposals_kind")
        ),
        sa.CheckConstraint(
            "language IN ('es', 'en')", name=op.f("ck_ai_proposals_language")
        ),
        sa.CheckConstraint(
            "provider IN ('anthropic', 'openai', 'groq')",
            name=op.f("ck_ai_proposals_provider"),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'invalid', 'rejected', 'failed')",
            name=op.f("ck_ai_proposals_status"),
        ),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND cost_micros >= 0",
            name=op.f("ck_ai_proposals_usage_not_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            name=op.f("fk_ai_proposals_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_ai_proposals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_proposals")),
    )
    op.create_index(
        "ix_ai_proposals_application_created",
        "ai_proposals",
        ["application_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ai_proposals_in_flight_updated_at",
        "ai_proposals",
        ["updated_at"],
        unique=False,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.create_index(
        "ix_ai_proposals_platform_usage",
        "ai_proposals",
        ["user_id", "kind"],
        unique=False,
        postgresql_where=sa.text("key_source = 'platform'"),
    )
    _replace_limit_key_check(_NEW_KEYS)


def downgrade() -> None:
    op.execute(
        "DELETE FROM user_limit_overrides "
        "WHERE limit_key IN ('ai_cv_proposals', 'ai_cover_letter_proposals')"
    )
    _replace_limit_key_check(_OLD_KEYS)
    op.drop_index(
        "ix_ai_proposals_platform_usage",
        table_name="ai_proposals",
        postgresql_where=sa.text("key_source = 'platform'"),
    )
    op.drop_index(
        "ix_ai_proposals_in_flight_updated_at",
        table_name="ai_proposals",
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )
    op.drop_index("ix_ai_proposals_application_created", table_name="ai_proposals")
    op.drop_table("ai_proposals")
    op.drop_table("ai_consents")
