import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.repositories.application_repository import ApplicationRepository


@pytest.mark.asyncio
async def test_add_returns_database_generated_id_and_created_at(
    db_session: AsyncSession,
):
    repository = ApplicationRepository(db_session)

    application = await repository.add(
        Application(position_title="Backend Developer", company_name="Acme")
    )

    assert application.id is not None
    assert application.created_at is not None
    assert application.created_at.tzinfo is not None


@pytest.mark.asyncio
async def test_list_paginates_and_reports_total(db_session: AsyncSession):
    repository = ApplicationRepository(db_session)
    for i in range(5):
        await repository.add(
            Application(position_title=f"Puesto {i}", company_name="Acme")
        )

    first_page, total = await repository.list(page=1, limit=2)
    last_page, _ = await repository.list(page=3, limit=2)

    assert total == 5
    assert len(first_page) == 2
    assert len(last_page) == 1


@pytest.mark.asyncio
async def test_list_pages_do_not_overlap(db_session: AsyncSession):
    # Recorrer todas las páginas debe devolver cada fila exactamente una vez. El
    # desempate por id mantiene el orden determinista incluso si dos filas
    # compartieran created_at (mismo microsegundo).
    repository = ApplicationRepository(db_session)
    for i in range(6):
        await repository.add(
            Application(position_title=f"Puesto {i}", company_name="Acme")
        )

    ids: list[uuid.UUID] = []
    for page in (1, 2, 3):
        items, _ = await repository.list(page=page, limit=2)
        ids.extend(item.id for item in items)

    assert len(ids) == 6
    assert len(set(ids)) == 6
