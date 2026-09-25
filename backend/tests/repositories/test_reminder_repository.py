from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.reminder_repository import ReminderFilters, ReminderRepository
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_reminder


async def _titles(
    session: AsyncSession,
    user: CurrentUser,
    filters: ReminderFilters | None = None,
    *,
    sort_by: str = "due_at",
    descending: bool = False,
) -> list[str]:
    items, _ = await ReminderRepository(session).list(
        user.id,
        filters or ReminderFilters(),
        page=1,
        limit=100,
        sort_by=sort_by,  # type: ignore[arg-type]
        descending=descending,
    )
    return [item.title for item in items]


@pytest.mark.asyncio
async def test_list_only_returns_own_reminders(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    await make_reminder(db_session, user.id, title="Mío")
    await make_reminder(db_session, other_user.id, title="Ajeno")

    assert await _titles(db_session, user) == ["Mío"]


@pytest.mark.asyncio
async def test_default_status_filter_is_pending(
    db_session: AsyncSession, user: CurrentUser
):
    now = datetime.now(UTC)
    await make_reminder(db_session, user.id, title="Pendiente", due_at=now)
    await make_reminder(
        db_session,
        user.id,
        title="Hecho",
        status="done",
        due_at=now + timedelta(days=1),
    )

    assert await _titles(db_session, user, ReminderFilters(statuses=["pending"])) == [
        "Pendiente"
    ]
    assert await _titles(db_session, user, ReminderFilters(statuses=[])) == [
        "Pendiente",
        "Hecho",
    ]


@pytest.mark.asyncio
async def test_filters_by_application(db_session: AsyncSession, user: CurrentUser):
    application = await make_application(db_session, user.id)
    await make_reminder(
        db_session, user.id, title="De la solicitud", application_id=application.id
    )
    await make_reminder(db_session, user.id, title="Suelto")

    reminders = await _titles(
        db_session, user, ReminderFilters(application_id=application.id)
    )
    assert reminders == ["De la solicitud"]


@pytest.mark.asyncio
async def test_due_range_filters(db_session: AsyncSession, user: CurrentUser):
    now = datetime.now(UTC)
    await make_reminder(db_session, user.id, title="Hoy", due_at=now)
    await make_reminder(
        db_session, user.id, title="Semana que viene", due_at=now + timedelta(days=7)
    )

    soon = ReminderFilters(due_before=now + timedelta(days=1))
    assert await _titles(db_session, user, soon) == ["Hoy"]


@pytest.mark.asyncio
async def test_count_includes_every_status(db_session: AsyncSession, user: CurrentUser):
    await make_reminder(db_session, user.id, status="pending")
    await make_reminder(db_session, user.id, status="done")
    await make_reminder(db_session, user.id, status="dismissed")

    assert await ReminderRepository(db_session).count(user.id) == 3


@pytest.mark.asyncio
async def test_list_includes_the_linked_application_summary(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, position_title="Dev")
    await make_reminder(db_session, user.id, application_id=application.id)

    items, _ = await ReminderRepository(db_session).list(
        user.id, ReminderFilters(), page=1, limit=10, sort_by="due_at", descending=False
    )

    assert items[0].application is not None
    assert items[0].application.position_title == "Dev"
