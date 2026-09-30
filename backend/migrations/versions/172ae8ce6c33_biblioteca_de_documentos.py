"""biblioteca de documentos

Revision ID: 172ae8ce6c33
Revises: f58741a45d81
Create Date: 2026-09-30 14:09:41.600458

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "172ae8ce6c33"
down_revision: str | Sequence[str] | None = "f58741a45d81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Valores congelados como texto: si LimitKey cambia, hace falta otra migración.
_OLD_KEYS = "'applications', 'companies', 'reminders'"
_NEW_KEYS = "'applications', 'companies', 'reminders', 'documents', 'storage_bytes'"
# storage_bytes NO: el almacenamiento tiene tope siempre (decisión del usuario en
# F11), también con una excepción por cuenta.
_NEW_UNLIMITED = "'applications', 'companies', 'reminders', 'documents'"


def _replace_override_checks(keys: str, unlimited: str) -> None:
    op.drop_constraint(
        op.f("ck_user_limit_overrides_limit_key"), "user_limit_overrides"
    )
    op.drop_constraint(
        op.f("ck_user_limit_overrides_unlimited_only_where_allowed"),
        "user_limit_overrides",
    )
    op.create_check_constraint(
        op.f("ck_user_limit_overrides_limit_key"),
        "user_limit_overrides",
        f"limit_key IN ({keys})",
    )
    op.create_check_constraint(
        op.f("ck_user_limit_overrides_unlimited_only_where_allowed"),
        "user_limit_overrides",
        f"value IS NOT NULL OR limit_key IN ({unlimited})",
    )


def upgrade() -> None:
    """F13: la biblioteca de documentos (RF-90…94) y sus dos límites."""
    op.create_table(
        "documents",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("storage_key", sa.String(length=300), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            "kind IN ('cv', 'cover_letter')", name=op.f("ck_documents_kind")
        ),
        sa.CheckConstraint(
            "origin IN ('uploaded', 'generated', 'ai_tailored')",
            name=op.f("ck_documents_origin"),
        ),
        sa.CheckConstraint(
            "status <> 'ready' OR storage_key IS NOT NULL",
            name=op.f("ck_documents_ready_has_storage_key"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'failed')", name=op.f("ck_documents_status")
        ),
        sa.CheckConstraint(
            "size_bytes >= 0", name=op.f("ck_documents_size_not_negative")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_documents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("id", "user_id", name=op.f("uq_documents_id_user_id")),
    )
    op.create_index(
        "ix_documents_user_id_created_at",
        "documents",
        ["user_id", "created_at"],
        unique=False,
    )
    # El almacenamiento va en bytes: una excepción de más de 2 GB no cabría.
    op.alter_column(
        "user_limit_overrides",
        "value",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )
    _replace_override_checks(_NEW_KEYS, _NEW_UNLIMITED)


def downgrade() -> None:
    # Las excepciones de las claves nuevas no caben en los CHECK antiguos.
    op.execute(
        "DELETE FROM user_limit_overrides "
        "WHERE limit_key IN ('documents', 'storage_bytes')"
    )
    _replace_override_checks(_OLD_KEYS, _OLD_KEYS)
    op.alter_column(
        "user_limit_overrides",
        "value",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )
    op.drop_index("ix_documents_user_id_created_at", table_name="documents")
    op.drop_table("documents")
