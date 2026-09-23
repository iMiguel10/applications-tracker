from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, LimitReachedError, NotFoundError
from app.models.reminder import Reminder
from app.schemas.reminder import ReminderCreate, ReminderListQuery
from app.schemas.user import CurrentUser
from app.services import reminder_service
from app.services.notifications.base import NotificationChannel
from app.services.reminder_service import ReminderService
from tests.factories import make_application, make_reminder


@pytest.mark.asyncio
async def test_create_without_application_is_allowed(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await ReminderService(db_session).create(
        user.id,
        ReminderCreate(
            title="Enviar el CV", due_at=datetime.now(UTC) + timedelta(days=1)
        ),
    )

    assert reminder.application_id is None
    assert reminder.status == "pending"


@pytest.mark.asyncio
async def test_create_with_a_foreign_application_is_not_found(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_application = await make_application(db_session, other_user.id)

    with pytest.raises(NotFoundError):
        await ReminderService(db_session).create(
            user.id,
            ReminderCreate(
                title="x",
                due_at=datetime.now(UTC) + timedelta(days=1),
                application_id=others_application.id,
            ),
        )


@pytest.mark.asyncio
async def test_create_fails_when_pending_limit_is_reached(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(reminder_service, "MAX_PENDING_REMINDERS_PER_USER", 1)
    await make_reminder(db_session, user.id)

    with pytest.raises(LimitReachedError) as error:
        await ReminderService(db_session).create(
            user.id,
            ReminderCreate(title="x", due_at=datetime.now(UTC) + timedelta(days=1)),
        )

    assert error.value.code == "reminders_limit_reached"


@pytest.mark.asyncio
async def test_done_and_dismissed_reminders_do_not_count_against_the_limit(
    db_session: AsyncSession, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(reminder_service, "MAX_PENDING_REMINDERS_PER_USER", 1)
    await make_reminder(db_session, user.id, status="done")
    await make_reminder(db_session, user.id, status="dismissed")

    reminder = await ReminderService(db_session).create(
        user.id,
        ReminderCreate(title="x", due_at=datetime.now(UTC) + timedelta(days=1)),
    )

    assert reminder.id is not None


@pytest.mark.asyncio
async def test_complete_sets_completed_at(db_session: AsyncSession, user: CurrentUser):
    reminder = await make_reminder(db_session, user.id)

    updated = await ReminderService(db_session).complete(user.id, reminder.id)

    assert updated.status == "done"
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_dismiss_does_not_set_completed_at(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await make_reminder(db_session, user.id)

    updated = await ReminderService(db_session).dismiss(user.id, reminder.id)

    assert updated.status == "dismissed"
    assert updated.completed_at is None


@pytest.mark.asyncio
async def test_cannot_complete_an_already_dismissed_reminder(
    db_session: AsyncSession, user: CurrentUser
):
    reminder = await make_reminder(db_session, user.id, status="dismissed")

    with pytest.raises(ConflictError) as error:
        await ReminderService(db_session).complete(user.id, reminder.id)

    assert error.value.code == "reminder_not_pending"


@pytest.mark.asyncio
async def test_complete_on_another_users_reminder_is_not_found(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_reminder = await make_reminder(db_session, other_user.id)

    with pytest.raises(NotFoundError):
        await ReminderService(db_session).complete(user.id, others_reminder.id)


@pytest.mark.asyncio
async def test_list_defaults_to_pending_only(
    db_session: AsyncSession, user: CurrentUser
):
    await make_reminder(db_session, user.id, title="Pendiente")
    await make_reminder(db_session, user.id, title="Hecho", status="done")

    items, total = await ReminderService(db_session).list(user.id, ReminderListQuery())

    assert total == 1
    assert items[0].title == "Pendiente"


@pytest.mark.asyncio
async def test_create_calls_the_notification_channel(
    db_session: AsyncSession, user: CurrentUser
):
    """La costura de RF-53: el service llama al canal inyectado, sea cual sea, en
    vez de conocer directamente InAppChannel."""

    class RecordingChannel(NotificationChannel):
        def __init__(self) -> None:
            self.sent: list[Reminder] = []

        async def send(self, reminder: Reminder) -> None:
            self.sent.append(reminder)

    channel = RecordingChannel()

    await ReminderService(db_session, channel=channel).create(
        user.id,
        ReminderCreate(title="x", due_at=datetime.now(UTC) + timedelta(days=1)),
    )

    assert len(channel.sent) == 1
