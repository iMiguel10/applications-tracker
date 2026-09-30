from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import enforce_unsubscribe_rate_limit, get_unsubscribe_service
from app.schemas.common import ErrorResponse, RateLimitedRead
from app.schemas.notification import UnsubscribeRead
from app.services.unsubscribe_service import UnsubscribeService

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
    # Públicos: sin sesión no hay límite por usuario, así que se limita por IP.
    dependencies=[Depends(enforce_unsubscribe_rate_limit)],
)

Token = Annotated[
    str,
    Query(
        max_length=200,
        description="El token del enlace de baja que llega en cada email de aviso.",
    ),
]
Service = Annotated[UnsubscribeService, Depends(get_unsubscribe_service)]
RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "model": ErrorResponse,
        "description": "Enlace de baja no válido (`invalid_unsubscribe_token`).",
    },
    429: {
        "model": RateLimitedRead,
        "description": "Demasiadas peticiones desde esta IP (30 por minuto). "
        "`Retry-After` dice cuántos segundos esperar.",
    },
}


@router.get(
    "/unsubscribe",
    summary="Consultar un enlace de baja de avisos",
    responses=RESPONSES,
)
async def describe_unsubscribe(token: Token, service: Service) -> UnsubscribeRead:
    """Dice de qué tipo de aviso es un enlace de baja, **sin aplicarla**: la página
    de la aplicación lo usa para pedir confirmación.

    Público: el token firmado identifica al usuario y el tipo de aviso. Un `GET`
    nunca da de baja a nadie, porque muchos servidores de correo abren los enlaces
    de los emails para analizarlos.
    """
    return UnsubscribeRead(kind=service.describe(token))


@router.post(
    "/unsubscribe",
    summary="Darse de baja de un tipo de aviso",
    responses=RESPONSES,
)
async def unsubscribe(token: Token, service: Service) -> UnsubscribeRead:
    """Desactiva el tipo de aviso del enlace para su usuario (RF-85). Idempotente.

    Público y sin cuerpo obligatorio: es también la URL de la cabecera
    `List-Unsubscribe` de cada email, a la que los clientes de correo hacen un
    `POST` con `List-Unsubscribe=One-Click` (RFC 8058) cuando se pulsa su botón de
    baja. El cuerpo se ignora.
    """
    return UnsubscribeRead(kind=await service.unsubscribe(token))
