import logging

import anthropic
import httpx2

from app.domain.ai import AiProvider
from app.infra.llm.base import (
    LLMAuthError,
    LLMError,
    LLMFinish,
    LLMQuotaError,
    LLMRejectedError,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

_FINISH = {
    "end_turn": LLMFinish.COMPLETE,
    "max_tokens": LLMFinish.TRUNCATED,
    "model_context_window_exceeded": LLMFinish.TRUNCATED,
    "refusal": LLMFinish.REFUSED,
}


class AnthropicProvider:
    """Adaptador de Anthropic con su SDK oficial (A31), para las claves propias.
    Salida estructurada con `output_config.format` (`json_schema`), que el modelo
    está obligado a cumplir.

    La API de mensajes no admite temperatura: el razonamiento se pide con
    `output_config.effort`. Sin reintentos (`max_retries=0`), como en Groq.
    """

    def __init__(
        self, *, timeout_seconds: float, http_client: httpx2.AsyncClient | None = None
    ) -> None:
        self._timeout = timeout_seconds
        # Solo para las pruebas (un transporte simulado). En producción, el del SDK.
        self._http_client = http_client

    @property
    def provider(self) -> AiProvider:
        return AiProvider.ANTHROPIC

    def _client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(
            api_key=api_key,
            timeout=self._timeout,
            max_retries=0,
            http_client=self._http_client,
        )

    async def complete(
        self, request: LLMRequest, *, model: str, api_key: str | None
    ) -> LLMResponse:
        client = self._client(api_key)
        output_config: anthropic.types.OutputConfigParam = {
            "format": {"type": "json_schema", "schema": dict(request.json_schema)}
        }
        if request.reasoning is not None:
            output_config["effort"] = request.reasoning
        try:
            message = await client.messages.create(
                model=model,
                max_tokens=request.max_output_tokens,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
                output_config=output_config,
            )
        except anthropic.APIError as exc:
            # `from None`: la excepción del SDK no viaja encadenada (ia.md §7).
            raise _translate(exc) from None
        finally:
            if self._http_client is None:
                await client.close()

        text = "".join(block.text for block in message.content if block.type == "text")
        return LLMResponse(
            text=text,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            finish=_FINISH.get(message.stop_reason or "", LLMFinish.COMPLETE),
        )

    async def check_access(self, *, model: str, api_key: str | None) -> None:
        # Pedir el modelo valida la clave y que existe, sin generar: no cuesta.
        client = self._client(api_key)
        try:
            await client.models.retrieve(model)
        except anthropic.APIError as exc:
            raise _translate(exc) from None
        finally:
            if self._http_client is None:
                await client.close()


def _translate(exc: anthropic.APIError) -> LLMError:
    """Error del SDK → `LLMError`. Al log va la clase y el código HTTP, nunca el
    mensaje ni el cuerpo del proveedor."""
    status = exc.status_code if isinstance(exc, anthropic.APIStatusError) else None
    logger.warning("Anthropic: %s (HTTP %s)", type(exc).__name__, status)

    if isinstance(exc, anthropic.APIConnectionError):
        return LLMUnavailableError()
    if isinstance(exc, anthropic.AuthenticationError | anthropic.PermissionDeniedError):
        return LLMAuthError(status_code=status)
    if isinstance(exc, anthropic.RateLimitError):
        return LLMQuotaError(status_code=status)
    # 529: sobrecargado; como un 5xx, "vuelve luego".
    if status is not None and status >= 500:
        return LLMUnavailableError(status_code=status)
    if status is not None:
        return LLMRejectedError(status_code=status)
    return LLMUnavailableError()
