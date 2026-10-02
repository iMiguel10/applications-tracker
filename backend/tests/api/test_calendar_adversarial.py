"""Pruebas adversas del calendario (QA de F17, RF-130, RF-131): rangos con desfase,
el tope de 62 días al segundo, archivadas, notas que nunca salen y enlaces entre
usuarios."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interview import InterviewOutcome
from app.models.reminder import Reminder
from app.schemas.user import CurrentUser
from tests.factories import (
    make_application,
    make_interview,
    make_reminder,
)

URL = "/api/v1/calendar/events"
START = datetime(2026, 10, 1, tzinfo=UTC)
END = datetime(2026, 11, 1, tzinfo=UTC)
DAY = datetime(2026, 10, 15, 9, tzinfo=UTC)

EVENT_KEYS = {
    "kind",
    "id",
    "starts_at",
    "duration_minutes",
    "title",
    "interview_type",
    "format",
    "interviewers",
    "outcome",
    "application",
}


async def _events(
    client: AsyncClient, start: str | None = None, end: str | None = None
) -> list[dict[str, Any]]:
    response = await client.get(
        URL,
        params={"start": start or START.isoformat(), "end": end or END.isoformat()},
    )
    assert response.status_code == 200, response.text
    return list(response.json()["events"])


@pytest.mark.asyncio
async def test_range_with_an_offset_is_compared_as_an_instant(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Medianoche del 1 de octubre en Madrid (+02:00) = 22:00 UTC del 30 de septiembre.
    application = await make_application(db_session, user.id)
    inside = await make_interview(
        db_session, application, scheduled_at=datetime(2026, 9, 30, 22, tzinfo=UTC)
    )
    await make_interview(
        db_session,
        application,
        scheduled_at=datetime(2026, 9, 30, 21, 59, 59, tzinfo=UTC),
    )

    events = await _events(
        client, start="2026-10-01T00:00:00+02:00", end="2026-10-02T00:00:00+02:00"
    )

    assert [e["id"] for e in events] == [str(inside.id)]


@pytest.mark.asyncio
async def test_a_range_one_second_over_62_days_is_rejected(client: AsyncClient):
    response = await client.get(
        URL,
        params={
            "start": START.isoformat(),
            "end": (START + timedelta(days=62, seconds=1)).isoformat(),
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_62_days_are_counted_in_real_time_across_offsets(client: AsyncClient):
    # 62 días de reloj entre -12:00 y +14:00 son 62 días y 26 horas reales.
    response = await client.get(
        URL,
        params={
            "start": "2026-10-01T00:00:00+14:00",
            "end": "2026-12-02T00:00:00-12:00",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unencoded_plus_in_the_offset_is_rejected_not_misread(
    client: AsyncClient,
):
    # En una query, "+" sin codificar es un espacio: la API no debe adivinar.
    response = await client.get(
        f"{URL}?start=2026-10-01T00:00:00+02:00&end=2026-10-20T00:00:00+02:00"
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome",
    [o.value for o in InterviewOutcome if o != InterviewOutcome.CANCELLED],
)
async def test_interviews_with_any_outcome_but_cancelled_are_listed(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser, outcome: str
):
    application = await make_application(db_session, user.id)
    interview = await make_interview(
        db_session, application, scheduled_at=DAY, outcome=outcome
    )

    events = await _events(client)

    assert [(e["id"], e["outcome"]) for e in events] == [(str(interview.id), outcome)]


@pytest.mark.asyncio
async def test_events_of_archived_applications_are_included(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    archived = await make_application(
        db_session, user.id, archived_at=datetime(2026, 9, 20, tzinfo=UTC)
    )
    interview = await make_interview(db_session, archived, scheduled_at=DAY)
    reminder = await make_reminder(
        db_session,
        user.id,
        due_at=DAY + timedelta(hours=1),
        application_id=archived.id,
    )

    events = await _events(client)

    assert [e["id"] for e in events] == [str(interview.id), str(reminder.id)]
    assert {e["application"]["id"] for e in events} == {str(archived.id)}


@pytest.mark.asyncio
async def test_each_event_carries_exactly_the_documented_fields_and_never_notes(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(
        db_session, user.id, notes="NOTA-SOLICITUD-PRIVADA"
    )
    await make_interview(
        db_session, application, scheduled_at=DAY, notes="NOTA-ENTREVISTA-PRIVADA"
    )
    await make_reminder(db_session, user.id, due_at=DAY, application_id=application.id)

    response = await client.get(
        URL, params={"start": START.isoformat(), "end": END.isoformat()}
    )

    assert response.status_code == 200
    assert "PRIVADA" not in response.text
    events = response.json()["events"]
    assert len(events) == 2
    for event in events:
        assert set(event) == EVENT_KEYS
        assert set(event["application"]) == {"id", "position_title", "company"}
        assert set(event["application"]["company"]) == {"id", "name"}


@pytest.mark.asyncio
async def test_other_user_cannot_link_a_reminder_to_my_application_nor_see_it(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    mine = await make_application(db_session, user.id, position_title="Mía")
    await make_interview(db_session, mine, scheduled_at=DAY)
    reminders_before = await db_session.scalar(select(func.count(Reminder.id)))

    as_user(other_user)
    created = await client.post(
        "/api/v1/reminders",
        json={
            "title": "Colarme en su calendario",
            "due_at": DAY.isoformat(),
            "application_id": str(mine.id),
        },
    )
    theirs = await _events(client)

    assert created.status_code == 404
    assert await db_session.scalar(select(func.count(Reminder.id))) == reminders_before
    assert theirs == []

    as_user(user)
    assert [e["application"]["id"] for e in await _events(client)] == [str(mine.id)]
