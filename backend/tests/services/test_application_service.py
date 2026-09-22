import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.schemas.application import ApplicationCreate
from app.services.application_service import ApplicationService


@pytest.mark.asyncio
async def test_create_commits_the_application(db_session: AsyncSession):
    service = ApplicationService(db_session)

    created = await service.create(
        ApplicationCreate(position_title="Backend Developer", company_name="Acme")
    )

    stored = await db_session.scalar(
        select(Application).where(Application.id == created.id)
    )
    assert stored is not None
    assert stored.position_title == "Backend Developer"
