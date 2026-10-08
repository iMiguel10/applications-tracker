"""Claves de API propias (F15 paso 5, RF-151, RF-153, ia.md §7): se validan con el
proveedor, se guardan cifradas, nunca vuelven en claro y la propuesta las usa sin
gastar usos gratuitos ni pasar en silencio a la clave de la plataforma (I4)."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import AppException
from app.domain.ai import AiProvider, AiTask, ProposalLanguage, ProposalStatus
from app.domain.limits import LimitKey
from app.infra.crypto import generate_master_key
from app.infra.llm import LLMAuthError, LLMQuotaError, LLMRejectedError
from app.infra.llm.fake import FakeLLMProvider
from app.infra.queue import InMemoryJobQueue
from app.models.user_limit_override import UserLimitOverride
from app.repositories.ai_consent_repository import AiConsentRepository
from app.repositories.ai_provider_key_repository import AiProviderKeyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai import AiProposalCreate
from app.schemas.user import CurrentUser
from app.services.ai_key_service import AiKeyService
from app.services.ai_proposal_service import AiProposalService
from tests.factories import make_application, make_profile_entry

USER_KEY = "sk-ant-user-1234567890abcdefKEY9"
PLATFORM_KEY = "gsk_platform_SECRET_keys"
CONFIG = Settings(
    **(
        settings.model_dump()
        | {
            "ai_platform_provider": "groq",
            "ai_platform_model": "openai/gpt-oss-120b",
            "ai_platform_api_key": PLATFORM_KEY,
            "ai_keys_encryption_keys": generate_master_key(),
            "ai_anthropic_models": "claude-sonnet-5-5,claude-haiku-5-5",
            "ai_openai_models": "",
            "ai_groq_models": "openai/gpt-oss-120b",
        }
    )
)
JOB_DESCRIPTION = "Backend con PostgreSQL, APIs REST y Kubernetes. " * 6
CV = AiProposalCreate(kind=AiTask.CV, language=ProposalLanguage.ES)


def providers() -> dict[AiProvider, FakeLLMProvider]:
    return {
        AiProvider.ANTHROPIC: FakeLLMProvider(provider_id=AiProvider.ANTHROPIC),
        AiProvider.GROQ: FakeLLMProvider(provider_id=AiProvider.GROQ),
    }


def keys(
    session: AsyncSession,
    fakes: dict[AiProvider, FakeLLMProvider],
    config: Settings = CONFIG,
) -> AiKeyService:
    return AiKeyService(session, config, providers=fakes)


async def code_of(call: Any) -> str:
    with pytest.raises(AppException) as caught:
        await call
    return caught.value.code


# --- Guardar, consultar y borrar ------------------------------------------------


@pytest.mark.asyncio
async def test_a_valid_key_is_checked_saved_encrypted_and_made_active(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    fakes = providers()

    overview = await keys(db_session, fakes).save(
        user.id, AiProvider.ANTHROPIC, f"  {USER_KEY}  ", None
    )

    # Comprobada con el proveedor (RF-153), con el modelo recomendado.
    assert fakes[AiProvider.ANTHROPIC].access_checks == [
        ("claude-sonnet-5-5", USER_KEY)
    ]
    stored = await AiProviderKeyRepository(db_session).get(
        user.id, AiProvider.ANTHROPIC
    )
    assert stored is not None
    assert USER_KEY.encode() not in stored.ciphertext
    assert stored.last4 == "KEY9"
    assert USER_KEY not in repr(stored)
    # La vista nunca lleva la clave; sí qué proveedores se ofrecen y la activa.
    assert USER_KEY not in overview.model_dump_json()
    assert overview.active_provider == AiProvider.ANTHROPIC
    assert [option.provider for option in overview.providers] == [
        AiProvider.ANTHROPIC,
        AiProvider.GROQ,
    ]
    anthropic = overview.providers[0]
    assert anthropic.key is not None and anthropic.key.last4 == "KEY9"
    assert await keys(db_session, fakes).decrypt(user.id, AiProvider.ANTHROPIC) == (
        USER_KEY
    )


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (LLMAuthError(status_code=401), "ai_key_invalid"),
        (LLMRejectedError(status_code=404), "ai_model_unavailable"),
        (LLMQuotaError(status_code=429), "ai_provider_quota"),
    ],
)
@pytest.mark.asyncio
async def test_a_key_the_provider_rejects_is_not_saved(
    db_session: AsyncSession, user: CurrentUser, error: Exception, code: str
) -> None:
    fakes = providers()
    fakes[AiProvider.ANTHROPIC].access_error = error  # type: ignore[assignment]

    caught = await code_of(
        keys(db_session, fakes).save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)
    )

    assert caught == code
    assert await AiProviderKeyRepository(db_session).list(user.id) == []
    db_user = await UserRepository(db_session).get_by_id(user.id)
    assert db_user is not None and db_user.ai_provider is None


@pytest.mark.asyncio
async def test_only_offered_providers_and_allowed_models(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    service = keys(db_session, providers())

    # OpenAI sin modelos en la lista; Ollama nunca con clave propia.
    for provider in (AiProvider.OPENAI, AiProvider.OLLAMA):
        assert await code_of(service.save(user.id, provider, USER_KEY, None)) == (
            "ai_provider_not_offered"
        )
    assert await code_of(
        service.save(user.id, AiProvider.ANTHROPIC, USER_KEY, "claude-opus-5-5")
    ) == ("ai_model_not_allowed")
    assert await code_of(
        service.save(user.id, AiProvider.ANTHROPIC, "corta", None)
    ) == ("ai_key_invalid")
    without_master_keys = keys(
        db_session,
        providers(),
        Settings(**(CONFIG.model_dump() | {"ai_keys_encryption_keys": ""})),
    )
    assert await code_of(
        without_master_keys.save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)
    ) == ("ai_provider_not_offered")


@pytest.mark.asyncio
async def test_change_model_delete_and_go_back_to_free_uses(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    fakes = providers()
    service = keys(db_session, fakes)
    await service.save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)

    changed = await service.change_model(
        user.id, AiProvider.ANTHROPIC, "claude-haiku-5-5"
    )
    assert changed.providers[0].key is not None
    assert changed.providers[0].key.model == "claude-haiku-5-5"
    assert fakes[AiProvider.ANTHROPIC].access_checks[-1] == (
        "claude-haiku-5-5",
        USER_KEY,
    )

    free = await service.set_active(user.id, None)
    assert free.active_provider is None
    assert (
        await code_of(service.set_active(user.id, AiProvider.GROQ)) == "ai_key_missing"
    )

    await service.set_active(user.id, AiProvider.ANTHROPIC)
    await service.delete(user.id, AiProvider.ANTHROPIC)
    # Borrar la activa vuelve a los usos gratuitos.
    after = await service.overview(user.id)
    assert after.active_provider is None
    assert after.providers[0].key is None
    assert await code_of(service.delete(user.id, AiProvider.ANTHROPIC)) == "not_found"


@pytest.mark.asyncio
async def test_another_users_key_is_invisible(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
) -> None:
    service = keys(db_session, providers())
    await service.save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)

    other = await service.overview(other_user.id)

    assert other.active_provider is None
    assert all(option.key is None for option in other.providers)
    assert await service.decrypt(other_user.id, AiProvider.ANTHROPIC) is None
    assert await code_of(service.delete(other_user.id, AiProvider.ANTHROPIC)) == (
        "not_found"
    )


@pytest.mark.asyncio
async def test_a_retired_model_must_be_changed_before_using_the_key(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    await keys(db_session, providers()).save(
        user.id, AiProvider.ANTHROPIC, USER_KEY, "claude-haiku-5-5"
    )
    narrower = Settings(
        **(CONFIG.model_dump() | {"ai_anthropic_models": "claude-sonnet-5-5"})
    )

    overview = await keys(db_session, providers(), narrower).overview(user.id)
    assert overview.providers[0].key is not None
    assert overview.providers[0].key.model_allowed is False
    assert await code_of(keys(db_session, providers(), narrower).active(user.id)) == (
        "ai_model_not_allowed"
    )


@pytest.mark.asyncio
async def test_deleting_the_account_deletes_its_keys(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    await keys(db_session, providers()).save(
        user.id, AiProvider.ANTHROPIC, USER_KEY, None
    )

    await UserRepository(db_session).delete(user.id)
    await db_session.flush()

    db_session.expunge_all()
    assert await AiProviderKeyRepository(db_session).list(user.id) == []


# --- Pedir y ejecutar una propuesta con la clave propia ------------------------------


async def prepared(session: AsyncSession, user: CurrentUser) -> uuid.UUID:
    await make_profile_entry(session, user.id, title="Backend", bullets=["APIs"])
    application = await make_application(
        session, user.id, job_description=JOB_DESCRIPTION
    )
    for provider in (AiProvider.ANTHROPIC, AiProvider.GROQ):
        await AiConsentRepository(session).grant(
            user.id, provider, 1, datetime.now(UTC)
        )
    await session.commit()
    return application.id


def proposals(
    session: AsyncSession, fakes: dict[AiProvider, FakeLLMProvider]
) -> AiProposalService:
    return AiProposalService(session, CONFIG, providers=fakes)


def answer() -> str:
    return json.dumps(
        {
            "insufficient_offer": False,
            "requirements": [],
            "summary": "Backend",
            "experiences": [{"entry_id": "e1", "bullets": []}],
            "skills": [],
        }
    )


@pytest.mark.asyncio
async def test_with_an_active_key_the_proposal_uses_it_and_no_free_use(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepared(db_session, user)
    fakes = providers()
    await keys(db_session, fakes).save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)
    # Sin usos gratuitos: con clave propia no importa (0017).
    db_session.add(
        UserLimitOverride(
            user_id=user.id, limit_key=LimitKey.AI_CV_PROPOSALS.value, value=0
        )
    )
    await db_session.commit()

    proposal = await proposals(db_session, fakes).request(
        user.id, application_id, CV, InMemoryJobQueue()
    )

    assert (proposal.key_source, proposal.provider, proposal.model) == (
        "user",
        "anthropic",
        "claude-sonnet-5-5",
    )
    fakes[AiProvider.ANTHROPIC].reply(answer())
    await proposals(db_session, fakes).run(user.id, proposal.id, datetime.now(UTC))
    await db_session.refresh(proposal)
    assert proposal.status == ProposalStatus.SUCCEEDED
    # El worker llama con la clave del usuario, descifrada, nunca con la de la
    # plataforma, y sin estimar un coste que no paga la plataforma.
    [call] = fakes[AiProvider.ANTHROPIC].calls
    assert call.api_key == USER_KEY
    assert fakes[AiProvider.GROQ].calls == []
    assert (proposal.billable, proposal.cost_micros) == (True, 0)


@pytest.mark.asyncio
async def test_an_own_key_needs_the_consent_of_its_provider(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepared(db_session, user)
    fakes = providers()
    await keys(db_session, fakes).save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)
    await AiConsentRepository(db_session).revoke(
        user.id, AiProvider.ANTHROPIC, datetime.now(UTC)
    )
    await db_session.commit()

    assert await code_of(
        proposals(db_session, fakes).request(
            user.id, application_id, CV, InMemoryJobQueue()
        )
    ) == ("ai_consent_required")


@pytest.mark.asyncio
async def test_a_failing_own_key_never_falls_back_to_the_platform(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # I4: con la clave propia inválida, error del proveedor y ninguna propuesta
    # con la clave de la plataforma.
    application_id = await prepared(db_session, user)
    fakes = providers()
    await keys(db_session, fakes).save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)
    proposal = await proposals(db_session, fakes).request(
        user.id, application_id, CV, InMemoryJobQueue()
    )
    fakes[AiProvider.ANTHROPIC].fail(LLMAuthError(status_code=401))

    await proposals(db_session, fakes).run(user.id, proposal.id, datetime.now(UTC))
    await db_session.refresh(proposal)

    assert (proposal.status, proposal.error_code) == ("failed", "ai_provider_auth")
    assert proposal.key_source == "user"
    assert fakes[AiProvider.GROQ].calls == []


@pytest.mark.asyncio
async def test_a_key_deleted_before_running_is_not_called(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepared(db_session, user)
    fakes = providers()
    await keys(db_session, fakes).save(user.id, AiProvider.ANTHROPIC, USER_KEY, None)
    proposal = await proposals(db_session, fakes).request(
        user.id, application_id, CV, InMemoryJobQueue()
    )
    await keys(db_session, fakes).delete(user.id, AiProvider.ANTHROPIC)

    await proposals(db_session, fakes).run(user.id, proposal.id, datetime.now(UTC))
    await db_session.refresh(proposal)

    assert (proposal.status, proposal.error_code) == ("failed", "ai_provider_auth")
    assert proposal.billable is False
    assert fakes[AiProvider.ANTHROPIC].calls == []
