import asyncio
import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.models.application import Application
from app.models.application_status_change import ApplicationStatusChange
from app.models.company import Company
from app.models.interview import Interview
from app.models.reminder import Reminder
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from tests.conftest import test_engine
from tests.factories import (
    make_application,
    make_company,
    make_interview,
    make_reminder,
    make_status_change,
)


@pytest.mark.asyncio
async def test_get_or_create_returns_same_user_on_second_call(
    db_session: AsyncSession,
):
    repository = UserRepository(db_session)

    first = await repository.get_or_create("st-user-1")
    second = await repository.get_or_create("st-user-1")

    assert first.id == second.id


@pytest.mark.asyncio
async def test_new_user_has_default_preferences(db_session: AsyncSession):
    user = await UserRepository(db_session).get_or_create("st-user-defaults")

    assert user.language is None
    assert user.stale_after_days == 14


@pytest.mark.asyncio
async def test_save_persists_changes_to_an_already_loaded_user(
    db_session: AsyncSession,
):
    repository = UserRepository(db_session)
    user = await repository.get_or_create("st-user-save")

    user.language = "en"
    user.stale_after_days = 30
    await repository.save(user)

    reloaded = await repository.get_by_id(user.id)
    assert reloaded is not None
    assert reloaded.language == "en"
    assert reloaded.stale_after_days == 30


@pytest.mark.asyncio
async def test_concurrent_get_or_create_creates_a_single_row():
    # T4: dos peticiones simultáneas del mismo usuario recién registrado.
    # Necesita dos transacciones reales e independientes, así que no usa el
    # fixture db_session (que lo metería todo en una sola) y limpia al final.
    supertokens_user_id = "st-concurrent-user"
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)
    try:
        user_a, user_b = await asyncio.gather(
            UserService(session_a).get_or_create(supertokens_user_id),
            UserService(session_b).get_or_create(supertokens_user_id),
        )

        async with AsyncSession(test_engine) as check:
            count = await check.scalar(
                select(func.count())
                .select_from(User)
                .where(User.supertokens_user_id == supertokens_user_id)
            )

        assert user_a.id == user_b.id
        assert count == 1
    finally:
        await session_a.close()
        await session_b.close()
        async with AsyncSession(test_engine) as cleanup:
            await cleanup.execute(
                delete(User).where(User.supertokens_user_id == supertokens_user_id)
            )
            await cleanup.commit()


@pytest.mark.asyncio
async def test_deleting_a_user_leaves_no_row_of_its_data_behind(
    db_session: AsyncSession,
):
    # Se buscan las filas por su propio id, no a través de la solicitud o del
    # usuario: tras el borrado esos caminos ya no existen y contarían 0 aunque
    # quedasen huérfanos.
    repository = UserRepository(db_session)
    owner = await repository.get_or_create("st-user-to-delete")
    company = await make_company(db_session, owner.id)
    application = await make_application(db_session, owner.id, company)
    change = await make_status_change(db_session, application, "interviewing")
    interview = await make_interview(db_session, application)
    linked = await make_reminder(db_session, owner.id, application_id=application.id)
    loose = await make_reminder(db_session, owner.id)
    initial_change_ids = (
        await db_session.scalars(
            select(ApplicationStatusChange.id).where(
                ApplicationStatusChange.application_id == application.id
            )
        )
    ).all()

    await repository.delete(owner.id)
    db_session.expunge_all()

    leftovers: dict[str, tuple[InstrumentedAttribute[uuid.UUID], list[uuid.UUID]]] = {
        "users": (User.id, [owner.id]),
        "companies": (Company.id, [company.id]),
        "applications": (Application.id, [application.id]),
        "history": (ApplicationStatusChange.id, [change.id, *initial_change_ids]),
        "interviews": (Interview.id, [interview.id]),
        "reminders": (Reminder.id, [linked.id, loose.id]),
    }
    counts = {
        name: await db_session.scalar(select(func.count()).where(column.in_(ids)))
        for name, (column, ids) in leftovers.items()
    }
    assert counts == dict.fromkeys(leftovers, 0)
