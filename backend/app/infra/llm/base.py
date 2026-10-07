from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Literal, Protocol

from app.domain.ai import AiProvider


@dataclass(frozen=True)
class LLMRequest:
    """Una petición con salida estructurada (A31): instrucciones, datos y el esquema
    que la respuesta debe cumplir. Nunca lleva la clave: va aparte, en cada llamada."""

    system: str
    user: str
    schema_name: str
    json_schema: Mapping[str, Any]
    max_output_tokens: int
    # Baja: la tarea es reordenar y reformular lo que hay, no crear. Con la del
    # proveedor (1 en Groq) el modelo adornaba más (ia.md §9). None: la del proveedor.
    temperature: float | None = None
    # Cuánto razona antes de responder, en los modelos que lo admiten. None: el del
    # adaptador.
    reasoning: Literal["low", "medium", "high"] | None = None


class LLMFinish(StrEnum):
    COMPLETE = "complete"
    # Se cortó al llegar a max_output_tokens: el JSON está incompleto.
    TRUNCATED = "truncated"
    # El proveedor se negó a responder (filtro de contenido).
    REFUSED = "refused"


@dataclass(frozen=True)
class LLMResponse:
    """Lo que devolvió el proveedor, sin interpretar: validar el texto contra el
    esquema y contra el perfil es cosa del service (A32). Que haya respuesta ya
    significa que se facturó (`billable`, ia.md §6)."""

    text: str
    input_tokens: int
    output_tokens: int
    finish: LLMFinish


class LLMError(Exception):
    """Un fallo del proveedor, traducido a un código estable que la interfaz explica.

    Nunca lleva el texto del proveedor: algunos repiten parte de la clave en el
    mensaje de error (ia.md §7, trampa). Solo el código, el HTTP y si se facturó.
    """

    code: ClassVar[str]
    # Por defecto el proveedor no llegó a generar nada: no se factura (ia.md §6).
    default_billable: ClassVar[bool] = False

    def __init__(self, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        self.billable = self.default_billable
        status = f"HTTP {status_code}" if status_code is not None else "sin respuesta"
        super().__init__(f"{self.code} ({status})")


class LLMAuthError(LLMError):
    """La clave no vale: inválida, revocada o sin permiso para ese modelo."""

    code = "ai_provider_auth"


class LLMQuotaError(LLMError):
    """El proveedor rechaza por límite de uso o saldo de esa cuenta."""

    code = "ai_provider_quota"


class LLMUnavailableError(LLMError):
    """No se pudo hablar con el proveedor: conexión, tiempo agotado o error suyo."""

    code = "ai_provider_unavailable"


class LLMRejectedError(LLMError):
    """El proveedor rechazó la petición: el modelo no existe o no admite lo que se
    le pide, o la entrada es demasiado grande. Suele ser un error de configuración."""

    code = "ai_provider_rejected"


class LLMInvalidOutputError(LLMError):
    """El modelo generó una respuesta que el propio proveedor descartó por no cumplir
    el esquema. Se generó, así que se factura: cuenta como una respuesta inválida."""

    code = "ai_response_invalid"
    default_billable = True


class LLMProvider(Protocol):
    """Un proveedor de IA (A31). Sin estado de clave: la recibe en cada llamada, para
    que la de un usuario no se quede en memoria más de lo que dura esa llamada."""

    @property
    def provider(self) -> AiProvider: ...

    async def complete(
        self, request: LLMRequest, *, model: str, api_key: str
    ) -> LLMResponse:
        """Pide la respuesta estructurada, sin reintentos: reintentar puede volver a
        facturar. Lanza un `LLMError` si el proveedor falla."""
        ...

    async def check_access(self, *, model: str, api_key: str) -> None:
        """Comprueba, sin coste o casi, que la clave vale y el modelo existe (RF-153).
        Lanza un `LLMError` si no."""
        ...
