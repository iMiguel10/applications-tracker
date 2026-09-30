"""Baja de avisos con el enlace del email, sin sesión (RF-85, segundo plano §5: B10)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.notifications import NotificationKind
from app.domain.unsubscribe import unsubscribe_token
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

URL = "/api/v1/notifications/unsubscribe"
KIND = NotificationKind.REMINDER_DUE


def _token(user: CurrentUser, kind: NotificationKind = KIND) -> str:
    return unsubscribe_token(user.id, kind, settings.app_secret)


async def _notifies(session: AsyncSession, user: CurrentUser) -> bool:
    loaded = await UserRepository(session).get_by_id(user.id)
    assert loaded is not None
    await session.refresh(loaded)
    return loaded.notify_reminder_due


@pytest.mark.asyncio
async def test_get_only_says_which_notification_it_is(
    anonymous_client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # B10: los escáneres de enlaces del correo hacen GET; no deben dar de baja.
    response = await anonymous_client.get(URL, params={"token": _token(user)})

    assert response.status_code == 200
    assert response.json() == {"kind": "reminder_due"}
    assert await _notifies(db_session, user) is True


@pytest.mark.asyncio
async def test_post_turns_off_only_that_notification(
    anonymous_client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    response = await anonymous_client.post(URL, params={"token": _token(user)})

    assert response.status_code == 200
    assert response.json() == {"kind": "reminder_due"}
    loaded = await UserRepository(db_session).get_by_id(user.id)
    assert loaded is not None
    await db_session.refresh(loaded)
    assert (loaded.notify_reminder_due, loaded.notify_interview) == (False, True)


@pytest.mark.asyncio
async def test_one_click_post_from_a_mail_client_works(
    anonymous_client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # RFC 8058: el cliente de correo hace POST a la URL de List-Unsubscribe con
    # este cuerpo de formulario.
    response = await anonymous_client.post(
        URL,
        params={"token": _token(user)},
        content="List-Unsubscribe=One-Click",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    assert await _notifies(db_session, user) is False


@pytest.mark.asyncio
async def test_unsubscribing_twice_is_fine(
    anonymous_client: AsyncClient, user: CurrentUser
):
    first = await anonymous_client.post(URL, params={"token": _token(user)})
    second = await anonymous_client.post(URL, params={"token": _token(user)})

    assert (first.status_code, second.status_code) == (200, 200)


@pytest.mark.asyncio
async def test_a_token_only_affects_its_own_user(
    anonymous_client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
):
    await anonymous_client.post(URL, params={"token": _token(other_user)})

    assert await _notifies(db_session, user) is True
    assert await _notifies(db_session, other_user) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_invalid_token_is_rejected(
    anonymous_client: AsyncClient, user: CurrentUser, method: str
):
    forged = _token(user)[:-2] + "xx"

    response = await anonymous_client.request(method, URL, params={"token": forged})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_unsubscribe_token"


@pytest.mark.asyncio
async def test_a_deleted_account_answers_like_any_other(
    anonymous_client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # El enlace no debe servir para saber si una cuenta sigue existiendo.
    token = _token(user)
    await UserRepository(db_session).delete(user.id)

    response = await anonymous_client.post(URL, params={"token": token})

    assert response.status_code == 200
