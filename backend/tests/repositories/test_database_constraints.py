"""La base de datos impone las reglas aunque el código de la aplicación falle.

Estas pruebas saltan los services a propósito: insertan directamente con los
repositories para comprobar que la BD es la última línea de defensa.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.repositories.application_repository import ApplicationRepository
from app.repositories.application_status_change_repository import (
    ApplicationStatusChangeRepository,
)
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_company


async def _assert_rejected(session: AsyncSession, application: Application) -> None:
    with pytest.raises(IntegrityError):
        await ApplicationRepository(session).add(application)
    await session.rollback()


@pytest.mark.asyncio
async def test_composite_fk_rejects_company_of_another_user(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    # T3 a nivel de BD (decisión A9): aunque el service olvidara comprobarlo.
    others_company = await make_company(db_session, other_user.id)

    await _assert_rejected(
        db_session,
        Application(
            user_id=user.id,
            company_id=others_company.id,
            position_title="Intruso",
            status="saved",
        ),
    )


@pytest.mark.asyncio
async def test_company_name_is_unique_per_user_ignoring_case(
    db_session: AsyncSession, user: CurrentUser
):
    await make_company(db_session, user.id, "Acme")

    with pytest.raises(IntegrityError):
        await make_company(db_session, user.id, "ACME")
    await db_session.rollback()


@pytest.mark.asyncio
async def test_two_users_can_have_a_company_with_the_same_name(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_company(db_session, user.id, "Acme")
    other = await make_company(db_session, other_user.id, "Acme")

    assert other.id is not None


@pytest.mark.asyncio
async def test_unknown_status_is_rejected(db_session: AsyncSession, user: CurrentUser):
    company = await make_company(db_session, user.id)

    await _assert_rejected(
        db_session,
        Application(
            user_id=user.id,
            company_id=company.id,
            position_title="X",
            status="ghosted",
            applied_at=date(2026, 9, 1),
        ),
    )


@pytest.mark.asyncio
async def test_sent_application_without_applied_at_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)

    await _assert_rejected(
        db_session,
        Application(
            user_id=user.id, company_id=company.id, position_title="X", status="applied"
        ),
    )


@pytest.mark.asyncio
async def test_saved_application_without_applied_at_is_accepted(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, status="saved", applied_at=None
    )

    assert application.applied_at is None


@pytest.mark.asyncio
async def test_inverted_salary_range_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)

    await _assert_rejected(
        db_session,
        Application(
            user_id=user.id,
            company_id=company.id,
            position_title="X",
            status="saved",
            salary_min=60000,
            salary_max=50000,
        ),
    )


@pytest.mark.asyncio
async def test_currency_must_be_iso_code(db_session: AsyncSession, user: CurrentUser):
    company = await make_company(db_session, user.id)

    await _assert_rejected(
        db_session,
        Application(
            user_id=user.id,
            company_id=company.id,
            position_title="X",
            status="saved",
            salary_currency="eur",
        ),
    )


@pytest.mark.asyncio
async def test_unknown_to_status_in_history_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)

    with pytest.raises(IntegrityError):
        await ApplicationStatusChangeRepository(db_session).add(
            ApplicationStatusChange(
                application_id=application.id,
                from_status="applied",
                to_status="ghosted",
                changed_at=datetime.now(UTC),
            )
        )
    await db_session.rollback()


@pytest.mark.asyncio
async def test_history_note_over_max_length_is_rejected(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)

    with pytest.raises(IntegrityError):
        await ApplicationStatusChangeRepository(db_session).add(
            ApplicationStatusChange(
                application_id=application.id,
                from_status="applied",
                to_status="screening",
                changed_at=datetime.now(UTC),
                note="x" * 5001,
            )
        )
    await db_session.rollback()
