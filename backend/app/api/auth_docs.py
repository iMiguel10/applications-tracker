"""Rutas /auth/* de SuperTokens declaradas SOLO para que aparezcan en el OpenAPI.

El middleware de SuperTokens intercepta estas rutas antes de que la petición llegue
al router de FastAPI, así que estos handlers nunca se ejecutan. Si algún día lo
hicieran (el middleware dejó de interceptarlas), responden 500 en vez de fingir
un login, y las pruebas de humo de auth (tests/api/test_auth_smoke.py) fallan.
"""

from typing import Annotated, Any, Literal, NoReturn

from fastapi import APIRouter, Header

from app.api.v1.deps import SECURITY_SCHEMES
from app.schemas.auth import (
    AuthCredentials,
    AuthFieldError,
    AuthOk,
    AuthResetInvalidToken,
    AuthStatusOk,
    AuthWrongCredentials,
    EmailAlreadyVerified,
    EmailVerifiedStatus,
    EmailVerifyInvalidToken,
    EmailVerifyRequest,
    PasswordResetRequest,
    PasswordResetTokenRequest,
    UnauthorizedError,
)
from app.schemas.common import RateLimitedRead

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


def _rate_limited(limit: str) -> dict[str, Any]:
    return {
        "model": RateLimitedRead,
        "description": f"Demasiados intentos ({limit}). `Retry-After` dice cuántos "
        "segundos esperar. Se frena, pero la cuenta nunca se bloquea.",
    }


def _served_by_middleware() -> NoReturn:
    raise RuntimeError(
        "Ruta servida por el middleware de SuperTokens: este handler solo documenta."
    )


@router.post(
    "/signup",
    summary="Registrarse",
    response_model=AuthOk | AuthFieldError,
    responses={
        200: {"headers": TOKEN_HEADERS},
        429: _rate_limited("5 por hora y por IP"),
    },
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
    responses={
        200: {"headers": TOKEN_HEADERS},
        429: _rate_limited("10 por minuto y por IP, y 10 por hora y por email"),
    },
)
async def signin(body: AuthCredentials, st_auth_mode: AuthMode = None) -> NoReturn:
    """Inicia sesión con email y contraseña.

    Responde siempre **200**: el resultado va en `status`. Para usar el resto de
    la API desde Swagger o una integración, toma la cabecera de respuesta
    `st-access-token` y envíala como `Authorization: Bearer <token>`.
    """
    _served_by_middleware()


@router.post(
    "/user/password/reset/token",
    summary="Pedir el email de recuperación de contraseña",
    response_model=AuthStatusOk | AuthFieldError,
    responses={429: _rate_limited("3 por hora y por email, y 10 por hora y por IP")},
)
async def password_reset_token(body: PasswordResetTokenRequest) -> NoReturn:
    """Envía al email indicado un enlace para elegir una contraseña nueva.

    Responde **200 `OK` exista o no una cuenta con ese email**: la respuesta no
    revela qué emails están registrados. Solo un email con formato no válido da
    `FIELD_ERROR`. El enlace lleva a
    `WEBSITE_DOMAIN/reset-password?token=…&tenantId=…`, caduca a la hora y sirve
    una sola vez. Si la instalación no tiene correo (`GET /api/v1/meta` →
    `email_enabled: false`), responde igual y no se envía nada.
    """
    _served_by_middleware()


@router.post(
    "/user/password/reset",
    summary="Guardar la contraseña nueva",
    response_model=AuthStatusOk | AuthResetInvalidToken | AuthFieldError,
)
async def password_reset(body: PasswordResetRequest) -> NoReturn:
    """Cambia la contraseña con el token del enlace del email y **cierra todas las
    sesiones** del usuario: ninguna se puede renovar después. Un access token ya
    emitido sigue siendo válido hasta que caduca (5 minutos como máximo).

    Responde siempre **200**: el resultado va en `status`. `FIELD_ERROR` indica
    una contraseña que no cumple la política (la misma que al registrarse).
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


@router.post(
    "/user/email/verify/token",
    summary="Reenviar el email de verificación",
    response_model=AuthStatusOk | EmailAlreadyVerified,
    dependencies=SECURITY_SCHEMES,
    responses={
        401: {"model": UnauthorizedError, "description": "Sin sesión."},
        429: _rate_limited("3 por hora y por usuario"),
    },
)
async def email_verify_token() -> NoReturn:
    """Envía otra vez el enlace de verificación al email de la sesión.

    El primero se envía solo al registrarse. Si la instalación no tiene correo
    (`GET /api/v1/meta` → `email_enabled: false`), responde igual y no se envía nada.
    """
    _served_by_middleware()


@router.post(
    "/user/email/verify",
    summary="Verificar el email",
    response_model=AuthStatusOk | EmailVerifyInvalidToken,
)
async def email_verify(body: EmailVerifyRequest) -> NoReturn:
    """Marca como verificado el email con el token del enlace. No requiere sesión:
    el enlace puede abrirse en otro dispositivo.

    Responde siempre **200**: el resultado va en `status`.
    """
    _served_by_middleware()


@router.get(
    "/user/email/verify",
    summary="Comprobar si el email está verificado",
    response_model=EmailVerifiedStatus,
    dependencies=SECURITY_SCHEMES,
    responses={401: {"model": UnauthorizedError, "description": "Sin sesión."}},
)
async def email_verify_status() -> NoReturn:
    """Dice si el email de la sesión está verificado.

    La API funciona sin verificar el email. Las rutas que lo exijan responderán
    **403** con `code: email_not_verified`; hoy ninguna lo exige todavía.
    """
    _served_by_middleware()
