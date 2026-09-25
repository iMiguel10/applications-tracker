"""Rate limiting de las rutas /auth/* de SuperTokens (RNF-04, límites y abuso §2).

Esas rutas las atiende el middleware de SuperTokens antes que el router, así que
no admiten dependencias de FastAPI: este middleware se coloca **por fuera** del de
SuperTokens (y por dentro de CORS, para que el 429 lleve sus cabeceras) y lo
alcanza primero.
"""

import json
import logging
from collections.abc import Awaitable, Callable
from http.cookies import SimpleCookie
from typing import Any

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from supertokens_python.exceptions import SuperTokensError
from supertokens_python.recipe.session.asyncio import (
    get_session_without_request_response,
)

from app.core.client_ip import client_ip, parse_trusted_proxies
from app.core.config import settings
from app.domain.rate_limits import AUTH_RULES, RateKey, RateRule
from app.infra.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

# Los formularios de /auth/* ocupan unos cientos de bytes. Leer el cuerpo entero
# para buscar el email no debe servir para agotar la memoria.
MAX_AUTH_BODY_BYTES = 64 * 1024


async def _buffer_body(receive: Receive) -> tuple[bytes | None, Receive]:
    """Lee el cuerpo y devuelve un `receive` que lo vuelve a entregar.

    El cuerpo de una petición ASGI se lee una sola vez: si este middleware lo
    consumiera sin más, SuperTokens recibiría un cuerpo vacío y respondería con un
    error de formato confuso (límites y abuso §2). None si supera el tamaño máximo.
    """
    messages: list[Message] = []
    size = 0
    while True:
        message = await receive()
        messages.append(message)
        if message["type"] != "http.request":
            break
        size += len(message.get("body", b""))
        if size > MAX_AUTH_BODY_BYTES:
            return None, receive
        if not message.get("more_body", False):
            break
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.request")

    async def replay() -> Message:
        if messages:
            return messages.pop(0)
        return await receive()

    return body, replay


def _email_from(body: bytes) -> str | None:
    try:
        data: Any = json.loads(body)
        fields = data.get("formFields", [])
        email = next(f.get("value") for f in fields if f.get("id") == "email")
    except (ValueError, AttributeError, StopIteration, TypeError):
        return None
    return email.strip().lower() if isinstance(email, str) and email.strip() else None


async def _user_from(headers: Headers) -> str | None:
    """El usuario de la sesión, validando el access token con el SDK (cookie o
    Bearer). Sin sesión válida, None: SuperTokens responderá 401 igualmente."""
    token = None
    authorization = headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    else:
        cookie = SimpleCookie(headers.get("cookie", ""))
        if "sAccessToken" in cookie:
            token = cookie["sAccessToken"].value
    if not token:
        return None
    try:
        session = await get_session_without_request_response(
            token, anti_csrf_check=False, session_required=False
        )
    except SuperTokensError:
        # Caducado o no válido: sin usuario que agrupar.
        return None
    return session.get_user_id() if session is not None else None


class AuthRateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        rules = (
            AUTH_RULES.get(scope.get("path", "")) if scope["type"] == "http" else None
        )
        if not rules or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        body, receive = await _buffer_body(receive)
        if body is None:
            await JSONResponse(
                {"detail": "Request body too large", "code": "payload_too_large"},
                status_code=413,
            )(scope, receive, send)
            return

        headers = Headers(scope=scope)
        limiter: RateLimiter = scope["app"].state.rate_limiter
        peer = scope["client"][0] if scope.get("client") else None
        ip = client_ip(
            peer,
            headers.get("x-forwarded-for"),
            parse_trusted_proxies(settings.trusted_proxies),
        )
        keys: dict[RateKey, Callable[[], Awaitable[str | None]]] = {
            RateKey.IP: lambda: _const(ip),
            RateKey.EMAIL: lambda: _const(_email_from(body)),
            RateKey.USER: lambda: _user_from(headers),
        }

        for rule in rules:
            if await self._blocked(
                limiter, rule, await keys[rule.key](), scope, receive, send
            ):
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _blocked(
        limiter: RateLimiter,
        rule: RateRule,
        key: str | None,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> bool:
        # Sin email en el cuerpo o sin sesión no hay por qué agrupar: SuperTokens
        # rechazará la petición igualmente (FIELD_ERROR o 401).
        if key is None:
            return False
        result = await limiter.hit(rule.limit, rule.name, rule.key.value, key)
        if result.allowed:
            return False
        logger.info("Rate limit %s por %s alcanzado", rule.name, rule.key.value)
        await JSONResponse(
            {
                "detail": "Too many requests",
                "code": "rate_limited",
                "retry_after": result.retry_after,
            },
            status_code=429,
            headers={"Retry-After": str(result.retry_after)},
        )(scope, receive, send)
        return True


async def _const(value: str | None) -> str | None:
    return value
