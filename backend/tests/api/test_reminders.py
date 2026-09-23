import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import CurrentUser
from app.services import reminder_service
from tests.factories import make_application, make_reminder


@pytest.mark.asyncio
async def test_create_reminder_linked_to_an_application(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, position_title="Dev")

    response = await client.post(
        "/api/v1/reminders",
        json={
            "title": "Enviar el test técnico",
            "due_at": "2026-10-01T10:00:00Z",
            "application_id": str(application.id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["channel"] == "in_app"
    assert body["sent_at"] is None
    assert body["application"] == {"id": str(application.id), "position_title": "Dev"}


@pytest.mark.asyncio
async def test_create_reminder_without_application(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    response = await client.post(
        "/api/v1/reminders",
        json={"title": "Actualizar el CV", "due_at": "2026-10-01T10:00:00Z"},
    )

    assert response.status_code == 201
    assert response.json()["application"] is None


@pytest.mark.asyncio
async def test_reminder_over_the_pending_limit_is_409(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(reminder_service, "MAX_PENDING_REMINDERS_PER_USER", 1)
    await make_reminder(db_session, user.id)

    response = await client.post(
        "/api/v1/reminders", json={"title": "x", "due_at": "2026-10-01T10:00:00Z"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "reminders_limit_reached"


@pytest.mark.asyncio
async def test_list_defaults_to_pending_and_sorted_by_due_date(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_reminder(db_session, user.id, title="Hecho", status="done")
    await make_reminder(
        db_session, user.id, title="Lejos", due_at=datetime(2026, 12, 1, 10, tzinfo=UTC)
    )
    await make_reminder(
        db_session, user.id, title="Cerca", due_at=datetime(2026, 10, 1, 10, tzinfo=UTC)
    )

    response = await client.get("/api/v1/reminders")

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["Cerca", "Lejos"]


@pytest.mark.asyncio
async def test_complete_then_dismiss_is_rejected(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    reminder = await make_reminder(db_session, user.id)

    completed = await client.post(f"/api/v1/reminders/{reminder.id}/complete")
    dismissed = await client.post(f"/api/v1/reminders/{reminder.id}/dismiss")

    assert completed.status_code == 200
    assert completed.json()["status"] == "done"
    assert dismissed.status_code == 409
    assert dismissed.json()["code"] == "reminder_not_pending"


@pytest.mark.asyncio
async def test_creating_with_unknown_application_is_404(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    response = await client.post(
        "/api/v1/reminders",
        json={
            "title": "x",
            "due_at": "2026-10-01T10:00:00Z",
            "application_id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 404
