import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.application_status_change_repository import (
    ApplicationStatusChangeRepository,
)
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_status_change


@pytest.mark.asyncio
async def test_list_for_application_orders_by_seq_descending(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="saved")
    await make_status_change(db_session, application, to_status="applied")
    await make_status_change(db_session, application, to_status="screening")

    changes = await ApplicationStatusChangeRepository(db_session).list_for_application(
        user.id, application.id
    )

    assert [change.to_status for change in changes] == [
        "screening",
        "applied",
        "saved",
    ]


@pytest.mark.asyncio
async def test_list_for_application_does_not_return_another_users_history(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_application = await make_application(db_session, other_user.id)

    changes = await ApplicationStatusChangeRepository(db_session).list_for_application(
        user.id, others_application.id
    )

    assert changes == []


@pytest.mark.asyncio
async def test_recent_returns_the_last_n_changes(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="saved")
    await make_status_change(db_session, application, to_status="applied")
    await make_status_change(db_session, application, to_status="screening")

    changes = await ApplicationStatusChangeRepository(db_session).recent(
        user.id, application.id, limit=2
    )

    assert [change.to_status for change in changes] == ["screening", "applied"]


@pytest.mark.asyncio
async def test_delete_removes_only_that_change(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id, status="saved")
    last = await make_status_change(db_session, application, to_status="applied")

    repository = ApplicationStatusChangeRepository(db_session)
    await repository.delete(last)

    changes = await repository.list_for_application(user.id, application.id)
    assert [change.to_status for change in changes] == ["saved"]
