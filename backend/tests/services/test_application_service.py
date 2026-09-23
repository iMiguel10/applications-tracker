import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, LimitReachedError, NotFoundError
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.schemas.user import CurrentUser
from app.services import application_service
from app.services.application_service import ApplicationService
from tests.factories import make_application, make_company


@pytest.mark.asyncio
async def test_create_applied_without_date_uses_today(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)

    created = await ApplicationService(db_session).create(
        user.id,
        ApplicationCreate(
            company_id=company.id, position_title="Dev", status="applied"
        ),
    )

    assert created.applied_at == datetime.now(UTC).date()
    assert created.origin == "manual"
    assert created.company.id == company.id


@pytest.mark.asyncio
async def test_create_saved_keeps_applied_at_empty(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id)

    created = await ApplicationService(db_session).create(
        user.id,
        ApplicationCreate(company_id=company.id, position_title="Dev", status="saved"),
    )

    assert created.applied_at is None


@pytest.mark.asyncio
async def test_create_with_unknown_company_is_not_found(
    db_session: AsyncSession, user: CurrentUser
):
    with pytest.raises(NotFoundError):
        await ApplicationService(db_session).create(
            user.id, ApplicationCreate(company_id=uuid.uuid4(), position_title="Dev")
        )


@pytest.mark.asyncio
async def test_create_fails_when_limit_is_reached(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(application_service, "MAX_APPLICATIONS_PER_USER", 1)
    existing = await make_application(db_session, user.id)

    with pytest.raises(LimitReachedError) as error:
        await ApplicationService(db_session).create(
            user.id,
            ApplicationCreate(company_id=existing.company_id, position_title="Otra"),
        )

    assert error.value.code == "applications_limit_reached"


@pytest.mark.asyncio
async def test_patch_validates_salary_against_stored_values(
    db_session: AsyncSession, user: CurrentUser
):
    # El schema solo ve lo enviado: la regla se comprueba sobre el resultado.
    application = await make_application(
        db_session, user.id, salary_min=40000, salary_max=50000
    )

    with pytest.raises(AppException) as error:
        await ApplicationService(db_session).update(
            user.id, application.id, ApplicationUpdate(salary_min=90000)
        )

    assert error.value.code == "salary_range_invalid"


@pytest.mark.asyncio
async def test_patch_cannot_clear_applied_at_of_a_sent_application(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, applied_at=date(2026, 9, 1)
    )

    with pytest.raises(AppException) as error:
        await ApplicationService(db_session).update(
            user.id, application.id, ApplicationUpdate(applied_at=None)
        )

    assert error.value.code == "applied_at_required"


@pytest.mark.asyncio
async def test_patch_only_changes_sent_fields(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, location="Madrid", salary_min=40000
    )

    updated = await ApplicationService(db_session).update(
        user.id, application.id, ApplicationUpdate(notes="Llamar el lunes")
    )

    assert updated.notes == "Llamar el lunes"
    assert updated.location == "Madrid"
    assert updated.salary_min == 40000


@pytest.mark.asyncio
async def test_patch_does_not_touch_last_activity(
    db_session: AsyncSession, user: CurrentUser
):
    # RF-64: editar datos no es actividad del proceso.
    application = await make_application(db_session, user.id)
    before = application.last_activity_at

    updated = await ApplicationService(db_session).update(
        user.id, application.id, ApplicationUpdate(notes="x")
    )

    assert updated.last_activity_at == before
    assert updated.updated_at > updated.created_at


@pytest.mark.asyncio
async def test_archive_is_idempotent(db_session: AsyncSession, user: CurrentUser):
    application = await make_application(db_session, user.id)
    service = ApplicationService(db_session)

    first = (await service.archive(user.id, application.id)).archived_at
    second = (await service.archive(user.id, application.id)).archived_at

    assert first is not None
    assert second == first


@pytest.mark.asyncio
async def test_export_csv_includes_archived_and_a_header_row(
    db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id, "Acme")
    await make_application(
        db_session, user.id, company, position_title="Backend Developer"
    )
    await make_application(
        db_session,
        user.id,
        company,
        position_title="Archivada",
        archived_at=datetime.now(UTC),
    )

    csv_text = await ApplicationService(db_session).export_csv(user.id)
    lines = csv_text.strip().splitlines()

    assert lines[0] == (
        "position_title,company,status,applied_at,work_mode,source,origin,"
        "location,job_url,salary_min,salary_max,salary_currency,notes,"
        "archived_at,created_at,updated_at"
    )
    assert len(lines) == 3
    assert "Backend Developer,Acme,applied" in lines[1]
    assert "Archivada,Acme,applied" in lines[2]


@pytest.mark.asyncio
async def test_export_csv_only_includes_the_users_own_applications(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_application(db_session, other_user.id, position_title="Ajena")

    csv_text = await ApplicationService(db_session).export_csv(user.id)
    header = (
        "position_title,company,status,applied_at,work_mode,source,origin,"
        "location,job_url,salary_min,salary_max,salary_currency,notes,"
        "archived_at,created_at,updated_at"
    )

    assert csv_text.strip().splitlines() == [header]
