import uuid
from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser

# NullPool: pytest-asyncio usa un event loop por test y una conexión de asyncpg
# no puede reutilizarse en otro loop. Sin pool, cada test abre la suya.
test_engine = create_async_engine(settings.database_url, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Sesión dentro de una transacción externa que se revierte al terminar el test.

    Con join_transaction_mode="create_savepoint", el commit() que hacen los services
    solo confirma un savepoint: el código bajo prueba es el mismo que en producción
    y la BD queda vacía entre tests, sea cual sea el orden de ejecución.
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


async def create_test_user(session: AsyncSession) -> CurrentUser:
    """Crea un usuario propio con un supertokens_user_id inventado (sin core)."""
    user = await UserRepository(session).get_or_create(f"test-{uuid.uuid4()}")
    return CurrentUser(id=user.id, supertokens_user_id=user.supertokens_user_id)


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> CurrentUser:
    return await create_test_user(db_session)


@pytest_asyncio.fixture
async def anonymous_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Cliente sin sesión: get_current_user es el real y responde 401."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def as_user() -> Callable[[CurrentUser], None]:
    """Cambia el usuario de la sesión: as_user(otro) hace que las peticiones
    siguientes se ejecuten como `otro`. Sustituye get_current_user entero, así que
    no interviene SuperTokens."""

    def _as_user(current_user: CurrentUser) -> None:
        app.dependency_overrides[get_current_user] = lambda: current_user

    return _as_user


@pytest_asyncio.fixture
async def client(
    anonymous_client: AsyncClient,
    user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
) -> AsyncClient:
    """Cliente autenticado como `user`, el caso por defecto de los tests de API."""
    as_user(user)
    return anonymous_client
