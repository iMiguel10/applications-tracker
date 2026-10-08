import logging

import httpx2
import openai

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
    "stop": LLMFinish.COMPLETE,
    "length": LLMFinish.TRUNCATED,
    "content_filter": LLMFinish.REFUSED,
}


class OpenAIProvider:
    """Adaptador de OpenAI con su SDK oficial (A31), para las claves propias.
    Salida estructurada estricta (`json_schema` con `strict`).

    Los modelos que se ofrecen (la familia GPT-5) razonan y no admiten otra
    temperatura que la suya: se pide solo `reasoning_effort`. Sin reintentos.
    """

    def __init__(
        self, *, timeout_seconds: float, http_client: httpx2.AsyncClient | None = None
    ) -> None:
        self._timeout = timeout_seconds
        # Solo para las pruebas (un transporte simulado). En producción, el del SDK.
        self._http_client = http_client

    @property
    def provider(self) -> AiProvider:
        return AiProvider.OPENAI

    def _client(self, api_key: str | None) -> openai.AsyncOpenAI:
        return openai.AsyncOpenAI(
            api_key=api_key,
            timeout=self._timeout,
            max_retries=0,
            http_client=self._http_client,
        )

    async def complete(
        self, request: LLMRequest, *, model: str, api_key: str | None
    ) -> LLMResponse:
        client = self._client(api_key)
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "developer", "content": request.system},
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
                reasoning_effort=(
                    openai.omit if request.reasoning is None else request.reasoning
                ),
            )
        except openai.APIError as exc:
            # `from None`: la excepción del SDK no viaja encadenada (ia.md §7).
            raise _translate(exc) from None
        finally:
            if self._http_client is None:
                await client.close()

        choice = completion.choices[0]
        usage = completion.usage
        finish = _FINISH.get(choice.finish_reason or "", LLMFinish.COMPLETE)
        if choice.message.refusal:
            finish = LLMFinish.REFUSED
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish=finish,
        )

    async def check_access(self, *, model: str, api_key: str | None) -> None:
        # Pedir el modelo valida la clave y que existe, sin generar: no cuesta.
        client = self._client(api_key)
        try:
            await client.models.retrieve(model)
        except openai.APIError as exc:
            raise _translate(exc) from None
        finally:
            if self._http_client is None:
                await client.close()


def _translate(exc: openai.APIError) -> LLMError:
    """Error del SDK → `LLMError`. Al log va la clase y el código HTTP, nunca el
    mensaje: OpenAI repite parte de la clave en el de una clave incorrecta."""
    status = exc.status_code if isinstance(exc, openai.APIStatusError) else None
    logger.warning("OpenAI: %s (HTTP %s)", type(exc).__name__, status)

    if isinstance(exc, openai.APIConnectionError):
        return LLMUnavailableError()
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        return LLMAuthError(status_code=status)
    if isinstance(exc, openai.RateLimitError):
        # También "sin saldo" (insufficient_quota): para el usuario, lo mismo.
        return LLMQuotaError(status_code=status)
    if status is not None and status >= 500:
        return LLMUnavailableError(status_code=status)
    if status is not None:
        return LLMRejectedError(status_code=status)
    return LLMUnavailableError()
