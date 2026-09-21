import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import engine
from app.main import app


@pytest_asyncio.fixture
async def client():
    await engine.dispose()

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client

    await engine.dispose()
