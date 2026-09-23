import asyncio

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from tests.conftest import test_engine


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
