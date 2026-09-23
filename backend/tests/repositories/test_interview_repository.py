from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interview_repository import InterviewRepository
from app.schemas.user import CurrentUser
from tests.factories import make_application, make_interview


@pytest.mark.asyncio
async def test_list_for_application_orders_by_scheduled_at(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    now = datetime.now(UTC)
    later = await make_interview(
        db_session, application, scheduled_at=now + timedelta(days=5)
    )
    sooner = await make_interview(
        db_session, application, scheduled_at=now + timedelta(days=1)
    )

    interviews = await InterviewRepository(db_session).list_for_application(
        user.id, application.id
    )

    assert [interview.id for interview in interviews] == [sooner.id, later.id]


@pytest.mark.asyncio
async def test_list_does_not_return_another_users_interviews(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_application = await make_application(db_session, other_user.id)
    await make_interview(db_session, others_application)

    interviews = await InterviewRepository(db_session).list_for_application(
        user.id, others_application.id
    )

    assert interviews == []


@pytest.mark.asyncio
async def test_get_does_not_return_another_users_interview(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_application = await make_application(db_session, other_user.id)
    interview = await make_interview(db_session, others_application)

    found = await InterviewRepository(db_session).get(
        user.id, others_application.id, interview.id
    )

    assert found is None


@pytest.mark.asyncio
async def test_delete_removes_only_that_interview(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    keep = await make_interview(db_session, application)
    remove = await make_interview(db_session, application)

    repository = InterviewRepository(db_session)
    await repository.delete(remove)

    remaining = await repository.list_for_application(user.id, application.id)
    assert [interview.id for interview in remaining] == [keep.id]
