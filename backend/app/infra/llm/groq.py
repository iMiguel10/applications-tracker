import logging
from typing import Literal

import groq
import httpx

from app.domain.ai import AiProvider
from app.infra.llm.base import (
    LLMAuthError,
    LLMError,
    LLMFinish,
    LLMInvalidOutputError,
    LLMQuotaError,
    LLMRejectedError,
    LLMRequest,
    LLMResponse,
    LLMUnavailableError,
)

logger = logging.getLogger(__name__)

ReasoningEffort = Literal["low", "medium", "high"]

# Groq responde 498 cuando su capacidad flexible está llena: es "vuelve luego".
_FLEX_AT_CAPACITY = 498

_FINISH = {
    "stop": LLMFinish.COMPLETE,
    "length": LLMFinish.TRUNCATED,
    "content_filter": LLMFinish.REFUSED,
}


class GroqProvider:
    """Adaptador de Groq con su SDK oficial (A31). Salida estructurada estricta
    (`json_schema` con `strict`), que en Groq tienen los modelos GPT-OSS.

    Sin reintentos (`max_retries=0`): un reintento automático tras un tiempo agotado
    podría facturar dos veces la misma propuesta.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float,
        reasoning_effort: ReasoningEffort = "medium",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._reasoning_effort = reasoning_effort
        # Solo para las pruebas (un transporte simulado). En producción, el del SDK.
        self._http_client = http_client

    @property
    def provider(self) -> AiProvider:
        return AiProvider.GROQ

    def _client(self, api_key: str) -> groq.AsyncGroq:
        return groq.AsyncGroq(
            api_key=api_key,
            timeout=self._timeout,
            max_retries=0,
            http_client=self._http_client,
        )

    async def complete(
        self, request: LLMRequest, *, model: str, api_key: str
    ) -> LLMResponse:
        client = self._client(api_key)
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": request.schema_name,
                        "strict": True,
                        "schema": dict(request.json_schema),
                    },
                },
                max_completion_tokens=request.max_output_tokens,
                reasoning_effort=self._reasoning_effort,
                # El razonamiento no se usa y ocuparía la respuesta.
                include_reasoning=False,
            )
        except groq.APIError as exc:
            # `from None`: la excepción del SDK no viaja encadenada, porque su mensaje
            # puede contener parte de la clave (ia.md §7, trampa).
            raise _translate(exc) from None
        finally:
            if self._http_client is None:
                await client.close()

        choice = completion.choices[0]
        usage = completion.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish=_FINISH.get(choice.finish_reason or "", LLMFinish.COMPLETE),
        )

    async def check_access(self, *, model: str, api_key: str) -> None:
        # Listar los modelos valida la clave y que el modelo existe, sin generar
        # nada: no cuesta. No sirve `models.retrieve(model)`: los ids de Groq llevan
        # barra (`openai/gpt-oss-120b`), la URL queda `/models/openai/gpt-oss-120b`
        # y responde 404 aunque el modelo exista.
        client = self._client(api_key)
        try:
            listing = await client.models.list()
        except groq.APIError as exc:
            raise _translate(exc) from None
        finally:
            if self._http_client is None:
                await client.close()
        if model not in {item.id for item in listing.data}:
            raise LLMRejectedError(status_code=404)


def _translate(exc: groq.APIError) -> LLMError:
    """Error del SDK → `LLMError`. Al log va la clase y el código HTTP, nunca el
    mensaje ni el cuerpo del proveedor."""
    status = exc.status_code if isinstance(exc, groq.APIStatusError) else None
    logger.warning("Groq: %s (HTTP %s)", type(exc).__name__, status)

    if isinstance(exc, groq.APIConnectionError):
        return LLMUnavailableError()
    if isinstance(exc, groq.AuthenticationError | groq.PermissionDeniedError):
        return LLMAuthError(status_code=status)
    if isinstance(exc, groq.RateLimitError):
        return LLMQuotaError(status_code=status)
    if isinstance(exc, groq.UnprocessableEntityError) or _schema_failed(exc):
        return LLMInvalidOutputError(status_code=status)
    if status is not None and (status >= 500 or status == _FLEX_AT_CAPACITY):
        return LLMUnavailableError(status_code=status)
    if status is not None:
        return LLMRejectedError(status_code=status)
    return LLMUnavailableError()


def _schema_failed(exc: groq.APIError) -> bool:
    """Groq descarta con un 400 `json_validate_failed` la respuesta que el modelo
    generó sin cumplir el esquema estricto. Solo se mira el código, no el texto."""
    if not isinstance(exc, groq.BadRequestError):
        return False
    body = exc.body
    error = body.get("error") if isinstance(body, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    return code == "json_validate_failed"
