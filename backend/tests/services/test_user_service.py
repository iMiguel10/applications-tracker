"""Borrado de cuenta cuando SuperTokens falla después del commit (decisión 0008).

El service confirma el borrado de los datos propios antes de llamar al core. Si esa
llamada falla, los datos ya no existen, el error no se silencia y la identidad
sigue viva para reintentarlo.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.user import User
from app.repositories.identity_repository import IdentityRepository
from app.schemas.user import CurrentUser
from app.services.user_service import UserService
from tests.factories import make_application, make_reminder


class IdentityStoreDown(Exception):
    pass


class FailingIdentities(IdentityRepository):
    """SuperTokens no responde al borrar la identidad."""

    def __init__(self) -> None:
        self.attempts = 0

    async def delete(self, supertokens_user_id: str) -> None:
        self.attempts += 1
        raise IdentityStoreDown("core unreachable")


class RecordingIdentities(IdentityRepository):
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def delete(self, supertokens_user_id: str) -> None:
        self.deleted.append(supertokens_user_id)


async def _users_with_id(session: AsyncSession, user_id: object) -> int:
    query = select(func.count()).select_from(User).where(User.id == user_id)
    return await session.scalar(query) or 0


async def _applications_of(session: AsyncSession, user_id: object) -> int:
    query = (
        select(func.count())
        .select_from(Application)
        .where(Application.user_id == user_id)
    )
    return await session.scalar(query) or 0


@pytest.mark.asyncio
async def test_identity_deletion_failure_propagates_after_own_data_is_deleted(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    await make_reminder(db_session, user.id, application_id=application.id)
    identities = FailingIdentities()

    with pytest.raises(IdentityStoreDown):
        await UserService(db_session, identities=identities).delete_account(user)

    assert identities.attempts == 1
    assert await _users_with_id(db_session, user.id) == 0
    assert await _applications_of(db_session, user.id) == 0


@pytest.mark.asyncio
async def test_account_deletion_can_be_retried_after_identity_deletion_failed(
    db_session: AsyncSession, user: CurrentUser
):
    await make_application(db_session, user.id)
    with pytest.raises(IdentityStoreDown):
        await UserService(db_session, identities=FailingIdentities()).delete_account(
            user
        )

    # La sesión sigue viva: la siguiente petición pasa por get_current_user, que
    # recrea una fila vacía para el mismo supertokens_user_id.
    retried_user = await UserService(db_session).get_or_create(user.supertokens_user_id)
    identities = RecordingIdentities()
    await UserService(db_session, identities=identities).delete_account(retried_user)

    assert identities.deleted == [user.supertokens_user_id]
    remaining = await db_session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.supertokens_user_id == user.supertokens_user_id)
    )
    assert remaining == 0
