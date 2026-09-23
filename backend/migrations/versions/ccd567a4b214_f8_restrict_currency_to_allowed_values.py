"""f8 restrict currency to allowed values

Revision ID: ccd567a4b214
Revises: c68b5a5b7bc2
Create Date: 2026-09-23 14:58:28.430670

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ccd567a4b214"
down_revision: str | Sequence[str] | None = "c68b5a5b7bc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Congelados como texto (trampa de autogenerate): si Currency cambia en domain/,
# esta migración no se actualiza sola.
_CURRENCIES = "'EUR', 'USD', 'GBP', 'CHF'"


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f("ck_applications_salary_currency_iso"), "applications", type_="check")
    op.create_check_constraint(
        op.f("ck_applications_salary_currency"),
        "applications",
        f"salary_currency IN ({_CURRENCIES})",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_applications_salary_currency"), "applications", type_="check")
    op.create_check_constraint(
        op.f("ck_applications_salary_currency_iso"),
        "applications",
        "salary_currency ~ '^[A-Z]{3}$'",
    )
