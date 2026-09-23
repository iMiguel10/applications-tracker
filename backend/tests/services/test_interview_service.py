import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.schemas.interview import InterviewCreate, InterviewUpdate
from app.schemas.user import CurrentUser
from app.services.interview_service import InterviewService
from tests.factories import make_application, make_interview


@pytest.mark.asyncio
async def test_create_touches_the_application_last_activity(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    before = application.last_activity_at

    await InterviewService(db_session).create(
        user.id,
        application.id,
        InterviewCreate(scheduled_at=datetime.now(UTC) + timedelta(days=2)),
    )

    assert application.last_activity_at > before


@pytest.mark.asyncio
async def test_create_on_unknown_application_is_not_found(
    db_session: AsyncSession, user: CurrentUser
):
    with pytest.raises(NotFoundError):
        await InterviewService(db_session).create(
            user.id,
            uuid.uuid4(),
            InterviewCreate(scheduled_at=datetime.now(UTC) + timedelta(days=2)),
        )


@pytest.mark.asyncio
async def test_update_sets_the_outcome(db_session: AsyncSession, user: CurrentUser):
    application = await make_application(db_session, user.id)
    interview = await make_interview(db_session, application)

    updated = await InterviewService(db_session).update(
        user.id, application.id, interview.id, InterviewUpdate(outcome="passed")
    )

    assert updated.outcome == "passed"


@pytest.mark.asyncio
async def test_update_only_changes_sent_fields(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    interview = await make_interview(db_session, application, interviewers="Laura")

    updated = await InterviewService(db_session).update(
        user.id, application.id, interview.id, InterviewUpdate(notes="Fue bien")
    )

    assert updated.notes == "Fue bien"
    assert updated.interviewers == "Laura"


@pytest.mark.asyncio
async def test_update_on_another_users_interview_is_not_found(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
):
    others_application = await make_application(db_session, other_user.id)
    interview = await make_interview(db_session, others_application)

    with pytest.raises(NotFoundError):
        await InterviewService(db_session).update(
            user.id, others_application.id, interview.id, InterviewUpdate(notes="x")
        )


@pytest.mark.asyncio
async def test_delete_removes_the_interview(
    db_session: AsyncSession, user: CurrentUser
):
    application = await make_application(db_session, user.id)
    interview = await make_interview(db_session, application)
    service = InterviewService(db_session)

    await service.delete(user.id, application.id, interview.id)

    assert await service.list(user.id, application.id) == []
