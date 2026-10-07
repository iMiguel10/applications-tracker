from dataclasses import dataclass, field

from app.domain.ai import AiProvider
from app.infra.llm.base import LLMError, LLMFinish, LLMRequest, LLMResponse


@dataclass(frozen=True)
class FakeCall:
    request: LLMRequest
    model: str
    api_key: str


@dataclass
class FakeLLMProvider:
    """Proveedor simulado para las pruebas (RNF-23): nunca llama a nadie. Devuelve,
    en orden, las respuestas o los errores grabados con `reply` y `fail`, y guarda
    cada llamada para comprobar qué se le envió (sin datos de contacto, ia.md I9)."""

    provider_id: AiProvider = AiProvider.GROQ
    calls: list[FakeCall] = field(default_factory=list)
    access_checks: list[tuple[str, str]] = field(default_factory=list)
    access_error: LLMError | None = None
    _queue: list[LLMResponse | LLMError] = field(default_factory=list)

    @property
    def provider(self) -> AiProvider:
        return self.provider_id

    def reply(
        self,
        text: str,
        *,
        input_tokens: int = 1_000,
        output_tokens: int = 500,
        finish: LLMFinish = LLMFinish.COMPLETE,
    ) -> None:
        self._queue.append(LLMResponse(text, input_tokens, output_tokens, finish))

    def fail(self, error: LLMError) -> None:
        self._queue.append(error)

    async def complete(
        self, request: LLMRequest, *, model: str, api_key: str
    ) -> LLMResponse:
        self.calls.append(FakeCall(request, model, api_key))
        if not self._queue:
            raise AssertionError("FakeLLMProvider: no hay respuesta grabada")
        result = self._queue.pop(0)
        if isinstance(result, LLMError):
            raise result
        return result

    async def check_access(self, *, model: str, api_key: str) -> None:
        self.access_checks.append((model, api_key))
        if self.access_error is not None:
            raise self.access_error
