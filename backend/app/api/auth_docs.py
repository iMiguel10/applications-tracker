"""Rutas /auth/* de SuperTokens declaradas SOLO para que aparezcan en el OpenAPI.

El middleware de SuperTokens intercepta estas rutas antes de que la petición llegue
al router de FastAPI, así que estos handlers nunca se ejecutan. Si algún día lo
hicieran (el middleware dejó de interceptarlas), responden 500 en vez de fingir
un login, y las pruebas de humo de auth (tests/api/test_auth_smoke.py) fallan.
"""

from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Header

from app.api.v1.deps import SECURITY_SCHEMES
from app.schemas.auth import (
    AuthCredentials,
    AuthFieldError,
    AuthOk,
    AuthStatusOk,
    AuthWrongCredentials,
    UnauthorizedError,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

AuthMode = Annotated[
    Literal["cookie", "header"] | None,
    Header(
        alias="st-auth-mode",
        description=(
            "Cómo se entregan los tokens. `header` (o sin la cabecera): en las "
            "cabeceras de respuesta `st-access-token` y `st-refresh-token`, para "
            "integraciones y Swagger. `cookie`: en cookies httpOnly, para navegadores."
        ),
    ),
]

TOKEN_HEADERS = {
    "st-access-token": {
        "description": "Access token (modo `header`). Enviarlo como "
        "`Authorization: Bearer <token>`. Caduca a los 5 minutos.",
        "schema": {"type": "string"},
    },
    "st-refresh-token": {
        "description": "Refresh token (modo `header`). Solo sirve para "
        "`POST /auth/session/refresh`.",
        "schema": {"type": "string"},
    },
    "front-token": {
        "description": "Carga del access token en Base64, sin firma. Informativa: "
        "no sirve para autenticarse.",
        "schema": {"type": "string"},
    },
}


def _served_by_middleware() -> NoReturn:
    raise RuntimeError(
        "Ruta servida por el middleware de SuperTokens: este handler solo documenta."
    )


@router.post(
    "/signup",
    summary="Registrarse",
    response_model=AuthOk | AuthFieldError,
    responses={200: {"headers": TOKEN_HEADERS}},
)
async def signup(body: AuthCredentials, st_auth_mode: AuthMode = None) -> NoReturn:
    """Crea la cuenta e inicia sesión en la misma llamada.

    Responde siempre **200**: el resultado va en `status`. `FIELD_ERROR` indica
    un email ya registrado o con formato no válido, o una contraseña que no
    cumple la política.
    """
    _served_by_middleware()


@router.post(
    "/signin",
    summary="Iniciar sesión",
    response_model=AuthOk | AuthWrongCredentials | AuthFieldError,
    responses={200: {"headers": TOKEN_HEADERS}},
)
async def signin(body: AuthCredentials, st_auth_mode: AuthMode = None) -> NoReturn:
    """Inicia sesión con email y contraseña.

    Responde siempre **200**: el resultado va en `status`. Para usar el resto de
    la API desde Swagger o una integración, toma la cabecera de respuesta
    `st-access-token` y envíala como `Authorization: Bearer <token>`.
    """
    _served_by_middleware()


@router.post(
    "/signout",
    summary="Cerrar sesión",
    response_model=AuthStatusOk,
    dependencies=SECURITY_SCHEMES,
    responses={401: {"model": UnauthorizedError, "description": "Sin sesión."}},
)
async def signout() -> NoReturn:
    """Revoca la sesión: el refresh token deja de servir al momento.

    Un access token ya emitido sigue siendo válido hasta que caduca (5 minutos
    como máximo).
    """
    _served_by_middleware()


@router.post(
    "/session/refresh",
    summary="Renovar la sesión",
    status_code=200,
    # Sin cuerpo útil (los tokens van en cabeceras): no hay modelo que inferir, y
    # el NoReturn de la firma no es un tipo de respuesta válido.
    response_model=None,
    responses={
        200: {"description": "Tokens nuevos.", "headers": TOKEN_HEADERS},
        401: {
            "model": UnauthorizedError,
            "description": "Refresh token inválido o revocado.",
        },
    },
)
async def refresh(st_auth_mode: AuthMode = None) -> NoReturn:
    """Emite un access token nuevo y rota el refresh token.

    En modo `header`, se envía el **refresh** token como `Authorization: Bearer`.
    Cada refresh token solo vale una vez: reutilizar uno ya rotado se trata como
    robo y revoca la sesión.
    """
    _served_by_middleware()
