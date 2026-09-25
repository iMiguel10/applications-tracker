import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_user_service
from app.main import app
from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.company import Company
from app.models.interview import Interview
from app.models.reminder import Reminder
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser
from app.services.user_service import UserService
from tests.factories import make_application, make_interview, make_reminder


class FakeIdentities(IdentityRepository):
    """Sustituye a SuperTokens: el test no necesita red ni core."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self.deleted: list[str] = []
        self.own_row_existed_on_delete: bool | None = None

    async def get_email(self, supertokens_user_id: str) -> str | None:
        return f"{supertokens_user_id}@example.com"

    async def delete(self, supertokens_user_id: str) -> None:
        # Registra si los datos propios ya no estaban al borrar la identidad: el
        # orden importa (arquitectura §4).
        assert self.session is not None
        self.own_row_existed_on_delete = (
            await self.session.scalar(
                select(User).where(User.supertokens_user_id == supertokens_user_id)
            )
            is not None
        )
        self.deleted.append(supertokens_user_id)


async def _count_owned(session: AsyncSession, user_id: object) -> dict[str, int]:
    app_ids = select(Application.id).where(Application.user_id == user_id)
    queries = {
        "users": select(func.count()).select_from(User).where(User.id == user_id),
        "companies": select(func.count())
        .select_from(Company)
        .where(Company.user_id == user_id),
        "applications": select(func.count())
        .select_from(Application)
        .where(Application.user_id == user_id),
        "history": select(func.count())
        .select_from(ApplicationStatusChange)
        .where(ApplicationStatusChange.application_id.in_(app_ids)),
        "interviews": select(func.count())
        .select_from(Interview)
        .where(Interview.application_id.in_(app_ids)),
        "reminders": select(func.count())
        .select_from(Reminder)
        .where(Reminder.user_id == user_id),
    }
    return {name: await session.scalar(query) or 0 for name, query in queries.items()}


@pytest.mark.asyncio
async def test_delete_account_removes_all_own_data_and_then_the_identity(
    client: AsyncClient,
    user: CurrentUser,
    other_user: CurrentUser,
    db_session: AsyncSession,
):
    for owner in (user, other_user):
        application = await make_application(db_session, owner.id)
        await make_interview(db_session, application)
        await make_reminder(db_session, owner.id, application_id=application.id)
        await make_reminder(db_session, owner.id)
    identities = FakeIdentities(db_session)
    app.dependency_overrides[get_user_service] = lambda: UserService(
        db_session, identities=identities
    )

    response = await client.delete("/api/v1/me")

    assert response.status_code == 204
    assert set((await _count_owned(db_session, user.id)).values()) == {0}
    assert identities.deleted == [user.supertokens_user_id]
    assert identities.own_row_existed_on_delete is False
    assert await _count_owned(db_session, other_user.id) == {
        "users": 1,
        "companies": 1,
        "applications": 1,
        "history": 1,
        "interviews": 1,
        "reminders": 2,
    }


@pytest.mark.asyncio
async def test_me_returns_own_id_and_email_from_identity_store(
    client: AsyncClient, user: CurrentUser, db_session: AsyncSession
):
    app.dependency_overrides[get_user_service] = lambda: UserService(
        db_session, identities=FakeIdentities()
    )

    response = await client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id),
        "email": f"{user.supertokens_user_id}@example.com",
    }


@pytest.mark.asyncio
async def test_preferences_default_to_no_language_14_days_and_no_timezone(
    client: AsyncClient, user: CurrentUser
):
    response = await client.get("/api/v1/me/preferences")

    assert response.status_code == 200
    assert response.json() == {
        "language": None,
        "stale_after_days": 14,
        "timezone": None,
    }


@pytest.mark.asyncio
async def test_updating_preferences_only_changes_sent_fields(
    client: AsyncClient, user: CurrentUser
):
    first = await client.patch("/api/v1/me/preferences", json={"language": "en"})
    assert first.json() == {"language": "en", "stale_after_days": 14, "timezone": None}

    second = await client.patch("/api/v1/me/preferences", json={"stale_after_days": 30})
    assert second.json() == {"language": "en", "stale_after_days": 30, "timezone": None}


@pytest.mark.asyncio
async def test_explicit_null_language_resets_to_follow_the_browser(
    client: AsyncClient, user: CurrentUser
):
    await client.patch("/api/v1/me/preferences", json={"language": "en"})

    response = await client.patch("/api/v1/me/preferences", json={"language": None})

    assert response.json()["language"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"language": "fr"},
        {"stale_after_days": 0},
        {"stale_after_days": 91},
        # A39: un nombre IANA, nunca un desfase ni una zona inventada.
        {"timezone": "+02:00"},
        {"timezone": "Europe/Atlantis"},
        {"timezone": "europe/madrid"},
        {"timezone": ""},
    ],
    ids=[
        "unknown_language",
        "threshold_too_low",
        "threshold_too_high",
        "timezone_offset",
        "timezone_unknown",
        "timezone_wrong_case",
        "timezone_empty",
    ],
)
async def test_invalid_preferences_are_rejected(
    client: AsyncClient, user: CurrentUser, payload: dict[str, object]
):
    response = await client.patch("/api/v1/me/preferences", json=payload)

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "timezone",
    [
        "Europe/Madrid",
        "America/Argentina/Buenos_Aires",
        "UTC",
        # Alias antiguos que siguen dando los navegadores (CLDR). La tzdata de la
        # imagen (Debian) no los trae; el paquete tzdata de Python, sí.
        "Asia/Calcutta",
        "Europe/Kiev",
        "America/Buenos_Aires",
    ],
)
async def test_timezone_is_saved_as_an_iana_name(
    client: AsyncClient, user: CurrentUser, timezone: str
):
    response = await client.patch("/api/v1/me/preferences", json={"timezone": timezone})

    assert response.status_code == 200
    assert response.json()["timezone"] == timezone
    assert (await client.get("/api/v1/me/preferences")).json()["timezone"] == timezone


class UnreachableIdentities(FakeIdentities):
    async def delete(self, supertokens_user_id: str) -> None:
        raise ConnectionError("SuperTokens core unreachable")


@pytest.mark.asyncio
async def test_delete_account_reports_500_when_identity_store_fails_after_commit(
    client: AsyncClient, user: CurrentUser, db_session: AsyncSession
):
    # El cliente no debe recibir un 204: sin él, el frontend no cierra sesión ni
    # vacía la caché, y el usuario puede reintentar (la identidad sigue viva).
    await make_application(db_session, user.id)
    app.dependency_overrides[get_user_service] = lambda: UserService(
        db_session, identities=UnreachableIdentities()
    )
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async with AsyncClient(transport=transport, base_url="http://test") as raw:
        response = await raw.delete("/api/v1/me")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert set((await _count_owned(db_session, user.id)).values()) == {0}
