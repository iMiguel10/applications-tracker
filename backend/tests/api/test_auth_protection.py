import re

import pytest
from httpx import AsyncClient

from app.main import app

PUBLIC_PATHS = {"/api/v1/health"}
DUMMY_ID = "00000000-0000-0000-0000-000000000000"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _protected_api_routes() -> list[tuple[str, str]]:
    """Todas las operaciones de /api/v1 que publica la app, salvo las públicas.

    Se leen del esquema OpenAPI y no de una lista escrita a mano: un endpoint nuevo
    queda cubierto por esta prueba sin tocarla (T1). Tampoco se recorre app.routes:
    FastAPI ya no copia ahí las rutas de los routers incluidos (las guarda en un
    _IncludedRouter interno), y el esquema OpenAPI es el contrato público.
    """
    routes = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/v1") or path in PUBLIC_PATHS:
            continue
        concrete_path = re.sub(r"\{[^}]+\}", DUMMY_ID, path)
        for method in operations:
            if method in HTTP_METHODS:
                routes.append((method.upper(), concrete_path))
    return sorted(routes)


def test_there_are_protected_routes_to_check():
    # Si el recorrido no encontrase rutas, T1 pasaría sin comprobar nada.
    assert len(_protected_api_routes()) >= 3


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "path"), _protected_api_routes())
async def test_protected_route_without_session_returns_401(
    anonymous_client: AsyncClient, method: str, path: str
):
    response = await anonymous_client.request(method, path)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_is_public(anonymous_client: AsyncClient):
    response = await anonymous_client.get("/api/v1/health")

    assert response.status_code == 200
