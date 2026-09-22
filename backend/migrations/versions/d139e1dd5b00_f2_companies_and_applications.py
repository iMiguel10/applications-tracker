"""f2 companies and applications

Revision ID: d139e1dd5b00
Revises: 7f2eb35d1c83
Create Date: 2026-09-22 16:53:22.016148

Escrita a mano sobre la base de autogenerate, que:
- no incluía los CHECK de `applications` (solo los detecta al crear una tabla), y
- añadía columnas NOT NULL sin default a una tabla con filas, lo que falla.

La tabla `applications` de F0 era desechable por diseño: se borra con sus datos y se
crea de nuevo. El downgrade restaura la tabla de F0 (vacía).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d139e1dd5b00"
down_revision: str | Sequence[str] | None = "7f2eb35d1c83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Congelados aquí a propósito: una migración describe el esquema de SU momento y
# no debe cambiar si mañana cambian los enums de domain/.
STATUSES = (
    "'saved', 'applied', 'screening', 'interviewing', 'offer', "
    "'accepted', 'rejected', 'withdrawn'"
)
WORK_MODES = "'onsite', 'hybrid', 'remote'"
SOURCES = (
    "'linkedin', 'infojobs', 'indeed', 'company_website', 'referral', "
    "'recruiter', 'other'"
)
ORIGINS = "'manual'"


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("applications")

    op.create_table(
        "companies",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "char_length(notes) <= 5000", name=op.f("ck_companies_notes_length")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_companies_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("id", "user_id", name=op.f("uq_companies_id_user_id")),
    )
    op.create_index(
        "uq_companies_user_id_lower_name",
        "companies",
        ["user_id", sa.literal_column("lower(name)")],
        unique=True,
    )

    op.create_table(
        "applications",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("position_title", sa.String(length=200), nullable=False),
        sa.Column("job_url", sa.String(length=2000), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("work_mode", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=True),
        sa.Column(
            "origin", sa.String(length=30), server_default="manual", nullable=False
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("applied_at", sa.Date(), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column(
            "salary_currency", sa.String(length=3), server_default="EUR", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            f"status IN ({STATUSES})", name=op.f("ck_applications_status")
        ),
        sa.CheckConstraint(
            f"work_mode IN ({WORK_MODES})", name=op.f("ck_applications_work_mode")
        ),
        sa.CheckConstraint(
            f"source IN ({SOURCES})", name=op.f("ck_applications_source")
        ),
        sa.CheckConstraint(
            f"origin IN ({ORIGINS})", name=op.f("ck_applications_origin")
        ),
        sa.CheckConstraint(
            "status IN ('saved', 'withdrawn') OR applied_at IS NOT NULL",
            name=op.f("ck_applications_applied_at_required"),
        ),
        sa.CheckConstraint(
            "salary_min >= 0", name=op.f("ck_applications_salary_min_non_negative")
        ),
        sa.CheckConstraint(
            "salary_max >= 0", name=op.f("ck_applications_salary_max_non_negative")
        ),
        sa.CheckConstraint(
            "salary_min <= salary_max", name=op.f("ck_applications_salary_range")
        ),
        sa.CheckConstraint(
            "salary_currency ~ '^[A-Z]{3}$'",
            name=op.f("ck_applications_salary_currency_iso"),
        ),
        sa.CheckConstraint(
            "char_length(notes) <= 5000", name=op.f("ck_applications_notes_length")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_applications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["companies.id", "companies.user_id"],
            name=op.f("fk_applications_company_id_companies"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("id", "user_id", name=op.f("uq_applications_id_user_id")),
    )
    op.create_index(
        "ix_applications_user_id_status", "applications", ["user_id", "status"]
    )
    op.create_index(
        "ix_applications_user_id_applied_at",
        "applications",
        ["user_id", sa.literal_column("applied_at DESC")],
    )
    op.create_index(
        "ix_applications_user_id_company_id", "applications", ["user_id", "company_id"]
    )
    op.create_index(
        "ix_applications_user_id_last_activity_at",
        "applications",
        ["user_id", "last_activity_at"],
    )


def downgrade() -> None:
    """Downgrade schema: vuelve a la tabla de F0 (sin datos)."""
    op.drop_table("applications")
    op.drop_index("uq_companies_user_id_lower_name", table_name="companies")
    op.drop_table("companies")

    op.create_table(
        "applications",
        sa.Column(
            "id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("position_title", sa.String(length=200), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
    )
