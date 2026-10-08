"""Los adaptadores de Anthropic, OpenAI y Ollama contra un transporte simulado (F15,
paso 5). Las mismas reglas que el de Groq (tests/infra/test_llm.py): el esquema
estricto, sin reintentos, errores traducidos y la clave nunca en un error (I7).

Anthropic y OpenAI usan `httpx2` (la bifurcación de httpx de sus SDK); Ollama,
`httpx`.
"""

import dataclasses
import json
import logging
import traceback
from typing import Any

import httpx
import httpx2
import pytest
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, settings
from app.domain.ai import AiProvider
from app.infra.llm import (
    LLMAuthError,
    LLMError,
    LLMFinish,
    LLMQuotaError,
    LLMRejectedError,
    LLMRequest,
    LLMUnavailableError,
    build_llm_providers,
    platform_model,
    strict_json_schema,
)
from app.infra.llm.anthropic import AnthropicProvider
from app.infra.llm.ollama import OllamaProvider
from app.infra.llm.openai import OpenAIProvider

API_KEY = "sk-secreta-1234567890abcdefSECRET"


class Proposal(BaseModel):
    summary: str


REQUEST = LLMRequest(
    system="instrucciones",
    user="datos",
    schema_name="proposal",
    json_schema=strict_json_schema(Proposal),
    max_output_tokens=4_000,
    temperature=0.4,
    reasoning="high",
)
ANSWER = '{"summary": "ok"}'


class Transport:
    """Responde siempre lo mismo y guarda cada petición recibida."""

    def __init__(self, status: int, body: dict[str, Any]) -> None:
        self.status = status
        self.body = body
        self.requests: list[Any] = []

    def __call__(self, request: Any) -> Any:
        self.requests.append(request)
        response_class = (
            httpx2.Response if isinstance(request, httpx2.Request) else httpx.Response
        )
        return response_class(self.status, json=self.body)


def assert_key_never_leaks(error: LLMError, caplog: pytest.LogCaptureFixture) -> None:
    rendered = "".join(traceback.format_exception(error))
    for text in (str(error), repr(error), repr(error.args), rendered, caplog.text):
        assert API_KEY not in text
        assert "SECRET" not in text
    assert error.__cause__ is None


# --- Anthropic --------------------------------------------------------------------


def anthropic(transport: Transport) -> AnthropicProvider:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(transport))
    return AnthropicProvider(timeout_seconds=5, http_client=client)


def message(stop_reason: str = "end_turn") -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-5-5",
        "content": [{"type": "text", "text": ANSWER}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 1234, "output_tokens": 567},
    }


def anthropic_error(kind: str, text: str) -> dict[str, Any]:
    return {"type": "error", "error": {"type": kind, "message": text}}


@pytest.mark.asyncio
async def test_anthropic_sends_the_schema_and_the_effort() -> None:
    transport = Transport(200, message())

    response = await anthropic(transport).complete(
        REQUEST, model="claude-sonnet-5-5", api_key=API_KEY
    )

    assert response.text == ANSWER
    assert (response.input_tokens, response.output_tokens) == (1234, 567)
    assert response.finish == LLMFinish.COMPLETE
    [sent] = transport.requests
    assert sent.headers["x-api-key"] == API_KEY
    body = json.loads(sent.content)
    assert body["system"] == "instrucciones"
    assert body["messages"] == [{"role": "user", "content": "datos"}]
    assert body["max_tokens"] == 4_000
    assert body["output_config"] == {
        "format": {"type": "json_schema", "schema": strict_json_schema(Proposal)},
        "effort": "high",
    }
    # La API de mensajes no admite temperatura.
    assert "temperature" not in body


@pytest.mark.parametrize(
    ("stop_reason", "finish"),
    [("max_tokens", LLMFinish.TRUNCATED), ("refusal", LLMFinish.REFUSED)],
)
@pytest.mark.asyncio
async def test_anthropic_reports_a_cut_or_refused_answer(
    stop_reason: str, finish: LLMFinish
) -> None:
    transport = Transport(200, message(stop_reason))

    response = await anthropic(transport).complete(REQUEST, model="m", api_key=API_KEY)

    assert response.finish == finish


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, LLMAuthError),
        (403, LLMAuthError),
        (429, LLMQuotaError),
        (500, LLMUnavailableError),
        (529, LLMUnavailableError),
        (404, LLMRejectedError),
        (400, LLMRejectedError),
        (422, LLMRejectedError),
    ],
)
@pytest.mark.asyncio
async def test_anthropic_translates_errors_without_retrying(
    status: int, error: type[LLMError]
) -> None:
    transport = Transport(status, anthropic_error("api_error", "x"))

    with pytest.raises(error) as caught:
        await anthropic(transport).complete(REQUEST, model="m", api_key=API_KEY)

    assert caught.value.billable is False
    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_anthropic_never_leaks_the_key(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    transport = Transport(
        401, anthropic_error("authentication_error", f"invalid x-api-key {API_KEY}")
    )

    with pytest.raises(LLMAuthError) as caught:
        await anthropic(transport).complete(REQUEST, model="m", api_key=API_KEY)

    assert_key_never_leaks(caught.value, caplog)


@pytest.mark.asyncio
async def test_anthropic_checks_access_by_reading_the_model() -> None:
    transport = Transport(
        200,
        {
            "id": "claude-sonnet-5-5",
            "type": "model",
            "display_name": "Claude Sonnet 5.5",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )

    await anthropic(transport).check_access(model="claude-sonnet-5-5", api_key=API_KEY)

    [sent] = transport.requests
    assert sent.method == "GET"
    assert sent.url.path.endswith("/models/claude-sonnet-5-5")


# --- OpenAI -------------------------------------------------------------------------


def openai(transport: Transport) -> OpenAIProvider:
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(transport))
    return OpenAIProvider(timeout_seconds=5, http_client=client)


def completion(finish: str = "stop", refusal: str | None = None) -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-5.5",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": ANSWER, "refusal": refusal},
                "finish_reason": finish,
            }
        ],
        "usage": {
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "total_tokens": 1801,
        },
    }


def openai_error(text: str, code: str | None = None) -> dict[str, Any]:
    return {"error": {"message": text, "type": "invalid_request_error", "code": code}}


@pytest.mark.asyncio
async def test_openai_sends_the_strict_schema_and_the_reasoning() -> None:
    transport = Transport(200, completion())

    response = await openai(transport).complete(
        REQUEST, model="gpt-5.5", api_key=API_KEY
    )

    assert response.text == ANSWER
    assert (response.input_tokens, response.output_tokens) == (1234, 567)
    [sent] = transport.requests
    assert sent.headers["authorization"] == f"Bearer {API_KEY}"
    body = json.loads(sent.content)
    assert body["messages"][0] == {"role": "developer", "content": "instrucciones"}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["max_completion_tokens"] == 4_000
    assert body["reasoning_effort"] == "high"
    # Los modelos GPT-5 razonan y no admiten otra temperatura que la suya.
    assert "temperature" not in body


@pytest.mark.asyncio
async def test_openai_without_reasoning_leaves_the_model_default() -> None:
    transport = Transport(200, completion())

    await openai(transport).complete(
        dataclasses.replace(REQUEST, reasoning=None), model="gpt-5.5", api_key=API_KEY
    )

    assert "reasoning_effort" not in json.loads(transport.requests[0].content)


@pytest.mark.asyncio
async def test_openai_reports_a_refusal() -> None:
    transport = Transport(200, completion(refusal="No puedo ayudar con eso"))

    response = await openai(transport).complete(REQUEST, model="m", api_key=API_KEY)

    assert response.finish == LLMFinish.REFUSED


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, LLMAuthError),
        (403, LLMAuthError),
        (429, LLMQuotaError),
        (500, LLMUnavailableError),
        (404, LLMRejectedError),
        (400, LLMRejectedError),
    ],
)
@pytest.mark.asyncio
async def test_openai_translates_errors_without_retrying(
    status: int, error: type[LLMError]
) -> None:
    transport = Transport(status, openai_error("x"))

    with pytest.raises(error):
        await openai(transport).complete(REQUEST, model="m", api_key=API_KEY)

    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_openai_never_leaks_the_key(caplog: pytest.LogCaptureFixture) -> None:
    # OpenAI repite parte de la clave en el error de una clave incorrecta.
    caplog.set_level(logging.DEBUG)
    transport = Transport(
        401, openai_error(f"Incorrect API key provided: {API_KEY}", "invalid_api_key")
    )

    with pytest.raises(LLMAuthError) as caught:
        await openai(transport).complete(REQUEST, model="m", api_key=API_KEY)

    assert_key_never_leaks(caught.value, caplog)


@pytest.mark.asyncio
async def test_openai_checks_access_by_reading_the_model() -> None:
    transport = Transport(
        200, {"id": "gpt-5.5", "object": "model", "created": 0, "owned_by": "openai"}
    )

    await openai(transport).check_access(model="gpt-5.5", api_key=API_KEY)

    assert transport.requests[0].url.path.endswith("/models/gpt-5.5")


# --- Ollama -------------------------------------------------------------------------


def ollama(transport: Any) -> OllamaProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    return OllamaProvider(
        base_url="http://ollama:11434/",
        timeout_seconds=5,
        context_tokens=8_192,
        http_client=client,
    )


def chat(done_reason: str = "stop") -> dict[str, Any]:
    return {
        "model": "gpt-oss:20b",
        "message": {"role": "assistant", "content": ANSWER},
        "done": True,
        "done_reason": done_reason,
        "prompt_eval_count": 1234,
        "eval_count": 567,
    }


@pytest.mark.asyncio
async def test_ollama_sends_the_schema_as_format() -> None:
    transport = Transport(200, chat())

    response = await ollama(transport).complete(
        REQUEST, model="gpt-oss:20b", api_key=None
    )

    assert response.text == ANSWER
    assert (response.input_tokens, response.output_tokens) == (1234, 567)
    [sent] = transport.requests
    assert str(sent.url) == "http://ollama:11434/api/chat"
    assert "authorization" not in sent.headers
    body = json.loads(sent.content)
    assert body["format"] == strict_json_schema(Proposal)
    assert body["stream"] is False
    # El contexto, siempre explícito: el de Ollama recortaría la entrada.
    assert body["options"] == {
        "num_ctx": 8_192,
        "num_predict": 4_000,
        "temperature": 0.4,
    }


@pytest.mark.asyncio
async def test_ollama_reports_a_cut_answer() -> None:
    response = await ollama(Transport(200, chat("length"))).complete(
        REQUEST, model="m", api_key=None
    )

    assert response.finish == LLMFinish.TRUNCATED


@pytest.mark.parametrize(
    ("status", "error"),
    [(404, LLMRejectedError), (400, LLMRejectedError), (500, LLMUnavailableError)],
)
@pytest.mark.asyncio
async def test_ollama_translates_errors(status: int, error: type[LLMError]) -> None:
    transport = Transport(status, {"error": "model 'x' not found"})

    with pytest.raises(error):
        await ollama(transport).complete(REQUEST, model="x", api_key=None)

    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_ollama_down_or_not_ollama_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    def html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>no soy Ollama</html>")

    for transport in (refuse, html):
        with pytest.raises(LLMUnavailableError) as caught:
            await ollama(transport).complete(REQUEST, model="m", api_key=None)
        assert caught.value.billable is False


@pytest.mark.asyncio
async def test_ollama_checks_the_model_is_downloaded() -> None:
    transport = Transport(
        200, {"models": [{"name": "gpt-oss:20b"}, {"name": "llama3.2:latest"}]}
    )
    provider = ollama(transport)

    await provider.check_access(model="gpt-oss:20b", api_key=None)
    await provider.check_access(model="llama3.2", api_key=None)
    with pytest.raises(LLMRejectedError):
        await provider.check_access(model="qwen3:8b", api_key=None)


# --- Configuración ------------------------------------------------------------------


def make_settings(**overrides: Any) -> Settings:
    return Settings(**(settings.model_dump() | overrides))


def test_ollama_as_platform_needs_its_address_but_no_key() -> None:
    config = make_settings(
        ai_platform_provider="ollama",
        ai_platform_model="gpt-oss:20b",
        ai_platform_api_key=None,
        ai_ollama_base_url="http://ollama:11434",
    )

    platform = platform_model(config)
    assert platform is not None
    assert (platform.provider, platform.api_key) == (AiProvider.OLLAMA, None)
    assert AiProvider.OLLAMA in build_llm_providers(config)
    with pytest.raises(ValidationError, match="AI_OLLAMA_BASE_URL"):
        make_settings(
            ai_platform_provider="ollama",
            ai_platform_model="gpt-oss:20b",
            ai_ollama_base_url=None,
        )


def test_without_its_address_there_is_no_ollama_adapter() -> None:
    assert AiProvider.OLLAMA not in build_llm_providers(
        make_settings(ai_ollama_base_url=None)
    )


def test_ollama_is_never_offered_for_own_keys() -> None:
    # Su dirección la fija quien despliega (SSRF) y su nube no impone el esquema.
    config = make_settings(ai_openai_models="gpt-5.5")

    assert config.ai_models(AiProvider.OLLAMA) == []
