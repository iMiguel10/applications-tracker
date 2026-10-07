"""`LLMProvider`: el adaptador de Groq contra un transporte simulado, el esquema
estricto y la configuración de la plataforma (F15, ia.md).

Ninguna prueba llama a un proveedor (RNF-23). Lo que más importa aquí es la
custodia de la clave: los errores del proveedor nunca la propagan (ia.md I7).
"""

import dataclasses
import json
import logging
import traceback
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings, settings
from app.domain.ai import AiProvider
from app.infra.llm import (
    LLMAuthError,
    LLMError,
    LLMFinish,
    LLMInvalidOutputError,
    LLMQuotaError,
    LLMRejectedError,
    LLMRequest,
    LLMUnavailableError,
    build_llm_providers,
    platform_model,
    strict_json_schema,
)
from app.infra.llm.groq import GroqProvider

API_KEY = "gsk_secreta_1234567890abcdefSECRET"
MODEL = "openai/gpt-oss-120b"


class Bullet(BaseModel):
    bullet_id: str
    text: str


class Entry(BaseModel):
    entry_id: str
    note: str | None = None
    bullets: list[Bullet] = Field(default_factory=list)


class Proposal(BaseModel):
    summary: str
    entries: list[Entry]


REQUEST = LLMRequest(
    system="instrucciones",
    user="datos",
    schema_name="proposal",
    json_schema=strict_json_schema(Proposal),
    max_output_tokens=4_000,
)


def completion(
    content: str = '{"summary": "ok", "entries": []}', finish: str = "stop"
) -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish,
            }
        ],
        "usage": {
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "total_tokens": 1801,
        },
    }


def error_body(message: str, code: str | None = None) -> dict[str, Any]:
    return {
        "error": {"message": message, "type": "invalid_request_error", "code": code}
    }


class Transport:
    """Responde siempre lo mismo y guarda cada petición recibida."""

    def __init__(self, status: int = 200, body: dict[str, Any] | None = None) -> None:
        self.status = status
        self.body = body if body is not None else completion()
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)


def provider(transport: Any) -> GroqProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    return GroqProvider(timeout_seconds=5, http_client=client)


# --- Respuestas -------------------------------------------------------------


@pytest.mark.asyncio
async def test_sends_the_strict_schema_and_reads_tokens() -> None:
    transport = Transport()

    response = await provider(transport).complete(REQUEST, model=MODEL, api_key=API_KEY)

    assert response.text == '{"summary": "ok", "entries": []}'
    assert (response.input_tokens, response.output_tokens) == (1234, 567)
    assert response.finish == LLMFinish.COMPLETE
    [sent] = transport.requests
    assert sent.headers["authorization"] == f"Bearer {API_KEY}"
    body = json.loads(sent.content)
    assert body["model"] == MODEL
    assert body["messages"] == [
        {"role": "system", "content": "instrucciones"},
        {"role": "user", "content": "datos"},
    ]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "proposal",
            "strict": True,
            "schema": strict_json_schema(Proposal),
        },
    }
    assert body["max_completion_tokens"] == 4_000
    assert body["include_reasoning"] is False
    # Sin pedir otra cosa, el razonamiento del adaptador y la temperatura del proveedor.
    assert body["reasoning_effort"] == "medium"
    assert "temperature" not in body


@pytest.mark.asyncio
async def test_sends_the_temperature_and_reasoning_of_the_request() -> None:
    transport = Transport()
    request = dataclasses.replace(REQUEST, temperature=0.4, reasoning="high")

    await provider(transport).complete(request, model=MODEL, api_key=API_KEY)

    body = json.loads(transport.requests[0].content)
    assert (body["temperature"], body["reasoning_effort"]) == (0.4, "high")


@pytest.mark.parametrize(
    ("finish_reason", "finish"),
    [("length", LLMFinish.TRUNCATED), ("content_filter", LLMFinish.REFUSED)],
)
@pytest.mark.asyncio
async def test_reports_a_cut_or_refused_answer(
    finish_reason: str, finish: LLMFinish
) -> None:
    transport = Transport(body=completion('{"summary": "a medi', finish_reason))

    response = await provider(transport).complete(REQUEST, model=MODEL, api_key=API_KEY)

    assert response.finish == finish


# --- Errores ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "body", "error", "billable"),
    [
        (401, error_body(f"Invalid API Key: {API_KEY}"), LLMAuthError, False),
        (403, error_body("forbidden"), LLMAuthError, False),
        (429, error_body("rate limit"), LLMQuotaError, False),
        (500, error_body("boom"), LLMUnavailableError, False),
        (503, error_body("overloaded"), LLMUnavailableError, False),
        (498, error_body("flex at capacity"), LLMUnavailableError, False),
        (404, error_body("model not found"), LLMRejectedError, False),
        (413, error_body("too large"), LLMRejectedError, False),
        (400, error_body("bad", "invalid_request"), LLMRejectedError, False),
        (
            400,
            error_body("Failed to validate JSON", "json_validate_failed"),
            LLMInvalidOutputError,
            True,
        ),
        (422, error_body("hallucinated"), LLMInvalidOutputError, True),
    ],
)
@pytest.mark.asyncio
async def test_translates_provider_errors(
    status: int, body: dict[str, Any], error: type[LLMError], billable: bool
) -> None:
    transport = Transport(status, body)

    with pytest.raises(error) as caught:
        await provider(transport).complete(REQUEST, model=MODEL, api_key=API_KEY)

    assert caught.value.status_code == status
    assert caught.value.billable is billable
    # Sin reintentos: reintentar podría facturar dos veces la misma propuesta.
    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_a_connection_failure_is_unavailable_and_not_billed() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(LLMUnavailableError) as caught:
        await provider(refuse).complete(REQUEST, model=MODEL, api_key=API_KEY)

    assert caught.value.billable is False
    assert caught.value.status_code is None


@pytest.mark.asyncio
async def test_the_key_never_leaves_a_provider_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Algunos proveedores repiten la clave en el mensaje de error (ia.md §7, I7).
    transport = Transport(401, error_body(f"Incorrect API key provided: {API_KEY}"))
    caplog.set_level(logging.DEBUG)

    with pytest.raises(LLMAuthError) as caught:
        await provider(transport).complete(REQUEST, model=MODEL, api_key=API_KEY)

    error = caught.value
    rendered = "".join(traceback.format_exception(error))
    for text in (str(error), repr(error), repr(error.args), rendered, caplog.text):
        assert API_KEY not in text
        assert "SECRET" not in text
    # La excepción del SDK, con el mensaje del proveedor, no viaja encadenada.
    assert error.__cause__ is None
    assert error.__suppress_context__ is True


def models_listing(*ids: str) -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {"id": id_, "object": "model", "created": 0, "owned_by": "x"} for id_ in ids
        ],
    }


@pytest.mark.asyncio
async def test_check_access_lists_the_models_without_generating() -> None:
    transport = Transport(body=models_listing("llama-3.3-70b-versatile", MODEL))

    await provider(transport).check_access(model=MODEL, api_key=API_KEY)

    [sent] = transport.requests
    assert sent.method == "GET"
    # Listar, no consultar uno: con la barra del id, /models/openai/gpt-oss-120b
    # da 404 aunque el modelo exista.
    assert sent.url.path.endswith("/models")


@pytest.mark.asyncio
async def test_check_access_with_a_model_the_account_lacks_is_rejected() -> None:
    transport = Transport(body=models_listing("llama-3.3-70b-versatile"))

    with pytest.raises(LLMRejectedError) as caught:
        await provider(transport).check_access(model=MODEL, api_key=API_KEY)

    assert caught.value.status_code == 404
    assert caught.value.billable is False


@pytest.mark.asyncio
async def test_check_access_with_a_bad_key_is_an_auth_error() -> None:
    transport = Transport(401, error_body(f"Invalid API Key: {API_KEY}"))

    with pytest.raises(LLMAuthError) as caught:
        await provider(transport).check_access(model=MODEL, api_key=API_KEY)

    assert API_KEY not in str(caught.value)


# --- Esquema estricto -------------------------------------------------------


def test_strict_schema_inlines_references_and_closes_every_object() -> None:
    schema = strict_json_schema(Proposal)

    assert "$defs" not in json.dumps(schema)
    assert "$ref" not in json.dumps(schema)
    assert "default" not in json.dumps(schema)
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["summary", "entries"]
    entry = schema["properties"]["entries"]["items"]
    assert entry["additionalProperties"] is False
    # Un campo opcional también es obligatorio: se expresa admitiendo null.
    assert entry["required"] == ["entry_id", "note", "bullets"]
    assert {"type": "null"} in entry["properties"]["note"]["anyOf"]
    bullet = entry["properties"]["bullets"]["items"]
    assert bullet["required"] == ["bullet_id", "text"]


def test_strict_schema_validates_back_with_pydantic() -> None:
    text = (
        '{"summary": "s", "entries": [{"entry_id": "e1", "note": null, "bullets": []}]}'
    )

    assert Proposal.model_validate_json(text).entries[0].entry_id == "e1"


def test_strict_schema_rejects_recursion() -> None:
    class Node(BaseModel):
        children: list["Node"]

    with pytest.raises(ValueError, match="recursivo"):
        strict_json_schema(Node)


# --- Configuración ----------------------------------------------------------


def make_settings(**overrides: Any) -> Settings:
    return Settings(**(settings.model_dump() | overrides))


def test_without_platform_provider_there_is_no_free_ai() -> None:
    assert platform_model(make_settings(ai_platform_provider=None)) is None
    assert platform_model(make_settings(ai_platform_provider="")) is None


def test_a_half_configured_platform_does_not_start() -> None:
    with pytest.raises(ValidationError, match="AI_PLATFORM_MODEL"):
        make_settings(ai_platform_provider="groq", ai_platform_model=MODEL)


def test_platform_model_never_shows_its_key() -> None:
    platform = platform_model(
        make_settings(
            ai_platform_provider="groq",
            ai_platform_model=MODEL,
            ai_platform_api_key=API_KEY,
        )
    )

    assert platform is not None
    assert platform.provider == AiProvider.GROQ
    assert platform.api_key == API_KEY
    assert API_KEY not in repr(platform)
    assert API_KEY not in str(platform)


def test_allowed_models_are_a_clean_ordered_list() -> None:
    config = make_settings(
        ai_openai_models=" gpt-a , gpt-b,,gpt-a ",
        ai_anthropic_models="",
    )

    assert config.ai_models(AiProvider.OPENAI) == ["gpt-a", "gpt-b"]
    assert config.ai_models(AiProvider.ANTHROPIC) == []


def test_every_built_adapter_is_the_provider_it_says() -> None:
    for name, adapter in build_llm_providers(settings).items():
        assert adapter.provider == name
