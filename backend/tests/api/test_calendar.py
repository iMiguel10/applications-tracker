"""Eventos del calendario (RF-130, RF-131): entrevistas y recordatorios pendientes
de un rango, solo del usuario, con su solicitud para enlazarlos."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from tests.factories import (
    make_application,
    make_company,
    make_interview,
    make_reminder,
)

START = datetime(2026, 10, 1, tzinfo=UTC)
END = datetime(2026, 11, 1, tzinfo=UTC)


async def _events(client: AsyncClient, **params: str) -> list[dict[str, Any]]:
    response = await client.get(
        "/api/v1/calendar/events",
        params={"start": START.isoformat(), "end": END.isoformat()} | params,
    )
    assert response.status_code == 200, response.text
    return list(response.json()["events"])


@pytest.mark.asyncio
async def test_lists_interviews_and_pending_reminders_in_order(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    company = await make_company(db_session, user.id, name="Globex")
    application = await make_application(
        db_session, user.id, company, position_title="Data engineer"
    )
    interview = await make_interview(
        db_session,
        application,
        scheduled_at=datetime(2026, 10, 10, 9, tzinfo=UTC),
        duration_minutes=45,
        interview_type="technical",
        format="online",
        notes="No debe salir",
    )
    linked = await make_reminder(
        db_session,
        user.id,
        title="Enviar el test",
        due_at=datetime(2026, 10, 5, 18, tzinfo=UTC),
        application_id=application.id,
    )
    loose = await make_reminder(
        db_session,
        user.id,
        title="Revisar LinkedIn",
        due_at=datetime(2026, 10, 20, tzinfo=UTC),
    )

    events = await _events(client)

    assert [(e["kind"], e["id"]) for e in events] == [
        ("reminder", str(linked.id)),
        ("interview", str(interview.id)),
        ("reminder", str(loose.id)),
    ]
    reminder, meeting, unlinked = events
    assert reminder["title"] == "Enviar el test"
    assert reminder["application"] == {
        "id": str(application.id),
        "position_title": "Data engineer",
        "company": {"id": str(company.id), "name": "Globex"},
    }
    assert meeting["duration_minutes"] == 45
    assert meeting["interview_type"] == "technical"
    assert meeting["format"] == "online"
    assert meeting["outcome"] == "pending"
    assert meeting["title"] is None
    assert meeting["application"]["company"]["name"] == "Globex"
    assert "notes" not in meeting
    assert unlinked["application"] is None


@pytest.mark.asyncio
async def test_the_range_includes_start_and_excludes_end(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    at_start = await make_interview(db_session, application, scheduled_at=START)
    await make_interview(db_session, application, scheduled_at=END)
    await make_interview(
        db_session, application, scheduled_at=START - timedelta(seconds=1)
    )
    at_end_reminder = await make_reminder(
        db_session, user.id, due_at=END - timedelta(seconds=1)
    )
    await make_reminder(db_session, user.id, due_at=END)

    events = await _events(client)

    assert {e["id"] for e in events} == {str(at_start.id), str(at_end_reminder.id)}


@pytest.mark.asyncio
async def test_leaves_out_cancelled_interviews_and_closed_reminders(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    day = datetime(2026, 10, 15, 10, tzinfo=UTC)
    passed = await make_interview(
        db_session, application, scheduled_at=day, outcome="passed"
    )
    await make_interview(db_session, application, scheduled_at=day, outcome="cancelled")
    pending = await make_reminder(db_session, user.id, due_at=day)
    await make_reminder(db_session, user.id, due_at=day, status="done")
    await make_reminder(db_session, user.id, due_at=day, status="dismissed")

    events = await _events(client)

    # A la misma hora, la entrevista antes que el recordatorio.
    assert [e["id"] for e in events] == [str(passed.id), str(pending.id)]


@pytest.mark.asyncio
async def test_includes_overdue_pending_reminders(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Un mes ya pasado: el recordatorio sigue pendiente y debe verse (vencido).
    overdue = await make_reminder(
        db_session, user.id, due_at=datetime(2026, 10, 2, tzinfo=UTC)
    )

    events = await _events(client)

    assert [e["id"] for e in events] == [str(overdue.id)]


@pytest.mark.asyncio
async def test_never_shows_another_users_events(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    day = datetime(2026, 10, 12, 10, tzinfo=UTC)
    theirs = await make_application(db_session, other_user.id)
    await make_interview(db_session, theirs, scheduled_at=day)
    await make_reminder(db_session, other_user.id, due_at=day)
    await make_reminder(db_session, other_user.id, due_at=day, application_id=theirs.id)
    mine = await make_reminder(db_session, user.id, due_at=day)

    events = await _events(client)

    assert [e["id"] for e in events] == [str(mine.id)]


@pytest.mark.asyncio
async def test_empty_range_answers_an_empty_list(client: AsyncClient):
    assert await _events(client) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-10-01T00:00:00Z", "end": "2026-10-01T00:00:00Z"},  # vacío
        {"start": "2026-10-10T00:00:00Z", "end": "2026-10-01T00:00:00Z"},  # al revés
        {"start": "2026-10-01T00:00:00Z", "end": "2026-12-03T00:00:00Z"},  # > 62 días
        {"start": "2026-10-01T00:00:00", "end": "2026-10-31T00:00:00"},  # sin zona
        {"start": "2026-10-01T00:00:00Z"},  # falta end
        {"start": "mañana", "end": "2026-10-31T00:00:00Z"},
    ],
)
async def test_rejects_an_invalid_range(client: AsyncClient, params: dict[str, str]):
    response = await client.get("/api/v1/calendar/events", params=params)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_a_range_of_exactly_62_days_is_allowed(client: AsyncClient):
    response = await client.get(
        "/api/v1/calendar/events",
        params={
            "start": START.isoformat(),
            "end": (START + timedelta(days=62)).isoformat(),
        },
    )

    assert response.status_code == 200
