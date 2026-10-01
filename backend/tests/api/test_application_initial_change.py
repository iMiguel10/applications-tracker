"""El cambio inicial de una solicitud enviada lleva la fecha de envío (0015): en el
historial, en el tablero y al editar la fecha mientras sea el único cambio."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from tests.factories import make_company

KIRITIMATI = ZoneInfo("Pacific/Kiritimati")  # UTC+14


def _today() -> date:
    return datetime.now(UTC).date()


async def _create(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    **fields: object,
) -> str:
    company = await make_company(db_session, user.id)
    response = await client.post(
        "/api/v1/applications",
        json={"company_id": str(company.id), "position_title": "Dev"} | fields,
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _history(client: AsyncClient, application_id: str) -> list[dict[str, str]]:
    response = await client.get(f"/api/v1/applications/{application_id}/status-changes")
    assert response.status_code == 200
    return list(response.json())


def _day(value: str) -> date:
    return datetime.fromisoformat(value).astimezone(UTC).date()


@pytest.mark.asyncio
async def test_applied_with_a_past_date_starts_on_that_day(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    sent = _today() - timedelta(days=12)

    application_id = await _create(
        client, db_session, user, status="applied", applied_at=sent.isoformat()
    )

    [initial] = await _history(client, application_id)
    assert initial["to_status"] == "applied"
    assert _day(initial["changed_at"]) == sent
    # El tablero cuenta los días desde ahí (RF-120).
    board = (await client.get("/api/v1/applications/board")).json()
    applied = next(c for c in board["columns"] if c["status"] == "applied")
    assert _day(applied["items"][0]["status_since"]) == sent


@pytest.mark.asyncio
async def test_the_day_is_taken_in_the_user_timezone(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    stored = await UserRepository(db_session).get_by_id(user.id)
    assert stored is not None
    stored.timezone = "Pacific/Kiritimati"
    await db_session.flush()
    local_today = datetime.now(UTC).astimezone(KIRITIMATI).date()
    sent = local_today - timedelta(days=3)

    application_id = await _create(
        client, db_session, user, status="applied", applied_at=sent.isoformat()
    )

    [initial] = await _history(client, application_id)
    changed_at = datetime.fromisoformat(initial["changed_at"])
    assert changed_at.astimezone(KIRITIMATI).date() == sent


@pytest.mark.asyncio
@pytest.mark.parametrize("days_ahead", [0, 5])
async def test_today_or_a_future_date_is_now(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser, days_ahead: int
):
    before = datetime.now(UTC)
    sent = _today() + timedelta(days=days_ahead)

    application_id = await _create(
        client, db_session, user, status="applied", applied_at=sent.isoformat()
    )

    [initial] = await _history(client, application_id)
    changed_at = datetime.fromisoformat(initial["changed_at"])
    assert before <= changed_at <= datetime.now(UTC)


@pytest.mark.asyncio
async def test_saved_starts_now_even_with_a_date(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # "Guardada" no ocurrió el día de envío: se guardó cuando se registró.
    before = datetime.now(UTC)

    application_id = await _create(
        client,
        db_session,
        user,
        status="saved",
        applied_at=(_today() - timedelta(days=10)).isoformat(),
    )

    [initial] = await _history(client, application_id)
    assert initial["to_status"] == "saved"
    assert datetime.fromisoformat(initial["changed_at"]) >= before


@pytest.mark.asyncio
async def test_a_later_change_can_be_dated_after_the_sent_day(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # Antes, el cambio inicial "ahora" impedía registrar una respuesta de hace una
    # semana a una candidatura apuntada hoy (changed_at_before_last_change).
    application_id = await _create(
        client,
        db_session,
        user,
        status="applied",
        applied_at=(_today() - timedelta(days=12)).isoformat(),
    )
    answered = datetime.now(UTC) - timedelta(days=7)

    response = await client.post(
        f"/api/v1/applications/{application_id}/status-changes",
        json={"to_status": "screening", "changed_at": answered.isoformat()},
    )

    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_editing_the_date_moves_the_only_change(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id = await _create(client, db_session, user, status="applied")
    corrected = _today() - timedelta(days=20)

    response = await client.patch(
        f"/api/v1/applications/{application_id}",
        json={"applied_at": corrected.isoformat()},
    )

    assert response.status_code == 200, response.text
    [initial] = await _history(client, application_id)
    assert _day(initial["changed_at"]) == corrected


@pytest.mark.asyncio
async def test_editing_the_date_leaves_the_history_alone_after_other_changes(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    sent = _today() - timedelta(days=12)
    application_id = await _create(
        client, db_session, user, status="applied", applied_at=sent.isoformat()
    )
    moved = await client.post(
        f"/api/v1/applications/{application_id}/status-changes",
        json={"to_status": "screening"},
    )
    assert moved.status_code == 201

    response = await client.patch(
        f"/api/v1/applications/{application_id}",
        json={"applied_at": (_today() - timedelta(days=30)).isoformat()},
    )

    assert response.status_code == 200
    latest, initial = await _history(client, application_id)
    assert latest["to_status"] == "screening"
    assert _day(initial["changed_at"]) == sent


@pytest.mark.asyncio
async def test_editing_other_fields_does_not_touch_the_history(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id = await _create(client, db_session, user, status="applied")
    [before] = await _history(client, application_id)

    response = await client.patch(
        f"/api/v1/applications/{application_id}", json={"notes": "Llamar el lunes"}
    )

    assert response.status_code == 200
    [after] = await _history(client, application_id)
    assert after["changed_at"] == before["changed_at"]
