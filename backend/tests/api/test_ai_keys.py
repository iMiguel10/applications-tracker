"""API de las claves de IA propias (F15 paso 5). Lo que más importa: la clave nunca
vuelve al cliente (I8), ni siquiera en un error, y cada usuario solo ve las suyas."""

from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_ai_key_service
from app.core.config import Settings, settings
from app.domain.ai import AiProvider
from app.infra.crypto import generate_master_key
from app.infra.llm import LLMAuthError
from app.infra.llm.fake import FakeLLMProvider
from app.main import app
from app.schemas.user import CurrentUser
from app.services.ai_key_service import AiKeyService
from tests.conftest import create_test_user

KEYS = "/api/v1/ai/keys"
USER_KEY = "sk-ant-api-1234567890abcdefSECRET"
CONFIG = Settings(
    **(
        settings.model_dump()
        | {
            "ai_keys_encryption_keys": generate_master_key(),
            "ai_anthropic_models": "claude-sonnet-5-5,claude-haiku-5-5",
            "ai_openai_models": "gpt-5.5,gpt-5.4-mini",
            "ai_groq_models": "",
        }
    )
)


@pytest.fixture
def fakes(db_session: AsyncSession) -> Iterator[dict[AiProvider, FakeLLMProvider]]:
    providers = {
        AiProvider.ANTHROPIC: FakeLLMProvider(provider_id=AiProvider.ANTHROPIC),
        AiProvider.OPENAI: FakeLLMProvider(provider_id=AiProvider.OPENAI),
    }
    app.dependency_overrides[get_ai_key_service] = lambda: AiKeyService(
        db_session, CONFIG, providers=providers
    )
    yield providers
    app.dependency_overrides.pop(get_ai_key_service, None)


@pytest.mark.asyncio
async def test_the_overview_lists_offered_providers_and_their_models(
    client: AsyncClient, fakes: dict[AiProvider, FakeLLMProvider]
):
    response = await client.get(KEYS)

    assert response.status_code == 200
    assert response.json() == {
        "own_keys_enabled": True,
        "providers": [
            {
                "provider": "anthropic",
                "models": ["claude-sonnet-5-5", "claude-haiku-5-5"],
                "key": None,
            },
            {"provider": "openai", "models": ["gpt-5.5", "gpt-5.4-mini"], "key": None},
        ],
        "active_provider": None,
    }


@pytest.mark.asyncio
async def test_saving_a_key_never_returns_it(
    client: AsyncClient, fakes: dict[AiProvider, FakeLLMProvider]
):
    # I8: ni al guardarla ni al consultarla vuelve la clave.
    saved = await client.put(
        f"{KEYS}/anthropic", json={"api_key": USER_KEY, "model": "claude-haiku-5-5"}
    )
    listed = await client.get(KEYS)

    assert saved.status_code == 200
    for response in (saved, listed):
        assert USER_KEY not in response.text
        assert "SECRET" not in response.text
    body = listed.json()
    assert body["active_provider"] == "anthropic"
    key = body["providers"][0]["key"]
    assert (key["model"], key["last4"], key["model_allowed"]) == (
        "claude-haiku-5-5",
        "CRET",
        True,
    )


@pytest.mark.asyncio
async def test_a_rejected_key_is_a_422_without_the_key(
    client: AsyncClient, fakes: dict[AiProvider, FakeLLMProvider]
):
    fakes[AiProvider.ANTHROPIC].access_error = LLMAuthError(status_code=401)

    response = await client.put(f"{KEYS}/anthropic", json={"api_key": USER_KEY})

    assert response.status_code == 422
    assert response.json()["code"] == "ai_key_invalid"
    assert USER_KEY not in response.text


@pytest.mark.asyncio
async def test_change_model_activate_and_delete(
    client: AsyncClient, fakes: dict[AiProvider, FakeLLMProvider]
):
    await client.put(f"{KEYS}/openai", json={"api_key": USER_KEY})

    changed = await client.patch(f"{KEYS}/openai", json={"model": "gpt-5.4-mini"})
    free = await client.put(f"{KEYS}/active", json={"provider": None})
    missing = await client.put(f"{KEYS}/active", json={"provider": "anthropic"})
    active = await client.put(f"{KEYS}/active", json={"provider": "openai"})
    deleted = await client.delete(f"{KEYS}/openai")
    after = await client.get(KEYS)

    assert changed.json()["providers"][1]["key"]["model"] == "gpt-5.4-mini"
    assert free.json()["active_provider"] is None
    assert (missing.status_code, missing.json()["code"]) == (409, "ai_key_missing")
    assert active.json()["active_provider"] == "openai"
    assert deleted.status_code == 204
    assert after.json()["active_provider"] is None


@pytest.mark.asyncio
async def test_providers_that_are_not_offered_are_refused(
    client: AsyncClient, fakes: dict[AiProvider, FakeLLMProvider]
):
    # Groq sin modelos en esta configuración; Ollama nunca con clave propia.
    for provider in ("groq", "ollama"):
        response = await client.put(f"{KEYS}/{provider}", json={"api_key": USER_KEY})
        assert (response.status_code, response.json()["code"]) == (
            422,
            "ai_provider_not_offered",
        )


@pytest.mark.asyncio
async def test_another_users_keys_are_invisible(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    fakes: dict[AiProvider, FakeLLMProvider],
):
    other = await create_test_user(db_session)
    await AiKeyService(db_session, CONFIG, providers=fakes).save(
        other.id, AiProvider.ANTHROPIC, USER_KEY, None
    )

    mine = await client.get(KEYS)
    delete = await client.delete(f"{KEYS}/anthropic")

    assert all(option["key"] is None for option in mine.json()["providers"])
    assert mine.json()["active_provider"] is None
    assert delete.status_code == 404
