"""Pruebas adversas de la API de IA (F15, ia.md §10, v2 §8 invariantes 13–17).

Aislamiento entre usuarios en propuestas, su `/document`, consentimientos y claves
propias; la clave nunca en un 422; y la cuota gratuita, que es "por cuenta y sin
renovación" (RF-150), no se recupera borrando la solicitud.
"""

import uuid
from collections.abc import Callable, Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    get_ai_consent_service,
    get_ai_key_service,
    get_ai_proposal_service,
    get_job_queue,
    get_limit_service,
)
from app.core.config import Settings, settings
from app.domain.ai import AiProvider
from app.infra.crypto import generate_master_key
from app.infra.llm.fake import FakeLLMProvider
from app.infra.queue import InMemoryJobQueue
from app.main import app
from app.models.ai_proposal import AiProposal
from app.models.document import Document
from app.repositories.ai_provider_key_repository import AiProviderKeyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import CurrentUser
from app.services.ai_consent_service import AiConsentService
from app.services.ai_key_service import AiKeyService
from app.services.ai_proposal_service import AiProposalService
from app.services.limit_service import LimitService
from tests.factories import make_ai_proposal, make_application, make_profile_entry

MODEL = "openai/gpt-oss-120b"
PLATFORM_KEY = "gsk_platform_SECRET_adversarial"
USER_KEY = "sk-ant-api-adversarial-0123456789SECRET"
CONFIG = Settings(
    **(
        settings.model_dump()
        | {
            "ai_platform_provider": "groq",
            "ai_platform_model": MODEL,
            "ai_platform_api_key": PLATFORM_KEY,
            "ai_keys_encryption_keys": generate_master_key(),
            "ai_anthropic_models": "claude-sonnet-5-5,claude-haiku-5-5",
            "ai_openai_models": "",
            "ai_groq_models": "",
        }
    )
)
JOB_DESCRIPTION = "Backend con PostgreSQL y APIs REST. " * 10
CONSENTS = "/api/v1/ai/consents"
KEYS = "/api/v1/ai/keys"
CV = {"kind": "cv", "language": "es"}


def proposals_url(application_id: object) -> str:
    return f"/api/v1/applications/{application_id}/ai-proposals"


@pytest.fixture
def queue() -> Iterator[InMemoryJobQueue]:
    job_queue = InMemoryJobQueue()
    app.dependency_overrides[get_job_queue] = lambda: job_queue
    yield job_queue
    app.dependency_overrides.pop(get_job_queue, None)


@pytest.fixture
def fakes(db_session: AsyncSession) -> Iterator[dict[AiProvider, FakeLLMProvider]]:
    """La instalación con IA de la plataforma (Groq) y claves propias de
    Anthropic, sin llamar a nadie."""
    providers = {
        AiProvider.ANTHROPIC: FakeLLMProvider(provider_id=AiProvider.ANTHROPIC),
        AiProvider.GROQ: FakeLLMProvider(provider_id=AiProvider.GROQ),
    }
    app.dependency_overrides[get_ai_proposal_service] = lambda: AiProposalService(
        db_session, CONFIG
    )
    app.dependency_overrides[get_ai_consent_service] = lambda: AiConsentService(
        db_session, CONFIG
    )
    app.dependency_overrides[get_limit_service] = lambda: LimitService(
        db_session, CONFIG
    )
    app.dependency_overrides[get_ai_key_service] = lambda: AiKeyService(
        db_session, CONFIG, providers=providers
    )
    yield providers
    for dependency in (
        get_ai_proposal_service,
        get_ai_consent_service,
        get_limit_service,
        get_ai_key_service,
    ):
        app.dependency_overrides.pop(dependency, None)


async def succeeded_proposal(
    db_session: AsyncSession, user: CurrentUser
) -> tuple[uuid.UUID, uuid.UUID, dict[str, object]]:
    """Una solicitud del usuario con una propuesta de CV terminada sobre su perfil,
    y la propuesta revisada que se enviaría para generar el PDF."""
    entry = await make_profile_entry(
        db_session, user.id, title="Backend", organization="Acme", bullets=["SQL"]
    )
    bullet = entry.bullets[0]
    application = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )
    proposal = await make_ai_proposal(
        db_session,
        application,
        status="succeeded",
        billable=True,
        proposal={
            "summary": "Propuesto",
            "experiences": [
                {
                    "entry_id": str(entry.id),
                    "bullets": [{"bullet_id": str(bullet.id), "text": "SQL afinado"}],
                }
            ],
            "skill_ids": [],
            "gaps": [],
        },
    )
    reviewed: dict[str, object] = {
        "summary": "Revisado",
        "experiences": [
            {
                "entry_id": str(entry.id),
                "bullets": [{"bullet_id": str(bullet.id), "text": "Optimicé SQL"}],
            }
        ],
        "skill_ids": [],
    }
    return application.id, proposal.id, reviewed


async def count_documents(db_session: AsyncSession) -> int:
    return (await db_session.scalar(select(func.count()).select_from(Document))) or 0


# --- Propuestas y su /document --------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("fakes")
async def test_other_user_gets_404_when_turning_a_proposal_into_a_document(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
    queue: InMemoryJobQueue,
):
    application_id, proposal_id, reviewed = await succeeded_proposal(db_session, user)
    documents_before = await count_documents(db_session)

    as_user(other_user)
    response = await client.post(
        f"{proposals_url(application_id)}/{proposal_id}/document",
        json={"design": "modern", "proposal": reviewed},
    )

    assert response.status_code == 404
    assert await count_documents(db_session) == documents_before
    assert queue.jobs == []


@pytest.mark.asyncio
@pytest.mark.usefixtures("fakes")
async def test_a_proposal_is_not_reachable_through_another_application(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
    queue: InMemoryJobQueue,
):
    # La propuesta de A pedida a través de una solicitud de B (la de B sí existe
    # para B) o a través de otra solicitud de A: 404 en los dos casos.
    application_id, proposal_id, reviewed = await succeeded_proposal(db_session, user)
    another_of_mine = await make_application(db_session, user.id)
    others = await make_application(db_session, other_user.id)

    through_mine = await client.get(
        f"{proposals_url(another_of_mine.id)}/{proposal_id}"
    )
    as_user(other_user)
    read = await client.get(f"{proposals_url(others.id)}/{proposal_id}")
    document = await client.post(
        f"{proposals_url(others.id)}/{proposal_id}/document",
        json={"design": "modern", "proposal": reviewed},
    )
    listing = await client.get(proposals_url(others.id))

    assert [through_mine.status_code, read.status_code, document.status_code] == [
        404,
        404,
        404,
    ]
    assert listing.status_code == 200
    assert listing.json() == []
    assert queue.jobs == []
    assert application_id


# --- Consentimientos -------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("fakes", "queue")
async def test_a_consent_belongs_only_to_the_user_who_gave_it(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    assert (await client.put(f"{CONSENTS}/groq")).status_code == 200

    as_user(other_user)
    await make_profile_entry(db_session, other_user.id, title="Backend")
    others_application = await make_application(
        db_session, other_user.id, job_description=JOB_DESCRIPTION
    )
    others_overview = (await client.get(CONSENTS)).json()
    others_request = await client.post(proposals_url(others_application.id), json=CV)
    others_revoke = await client.delete(f"{CONSENTS}/groq")

    as_user(user)
    mine = (await client.get(CONSENTS)).json()

    assert others_overview["consents"] == []
    assert (others_request.status_code, others_request.json()["code"]) == (
        409,
        "ai_consent_required",
    )
    # Retirar "el suyo" no toca el de A.
    assert others_revoke.status_code == 204
    [consent] = mine["consents"]
    assert (consent["provider"], consent["granted"]) == ("groq", True)


# --- Claves propias ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_other_user_cannot_activate_change_or_delete_a_key_they_do_not_have(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
    fakes: dict[AiProvider, FakeLLMProvider],
):
    await AiKeyService(db_session, CONFIG, providers=fakes).save(
        user.id, AiProvider.ANTHROPIC, USER_KEY, None
    )

    as_user(other_user)
    activate = await client.put(f"{KEYS}/active", json={"provider": "anthropic"})
    change = await client.patch(f"{KEYS}/anthropic", json={"model": "claude-haiku-5-5"})
    delete = await client.delete(f"{KEYS}/anthropic")

    assert (activate.status_code, activate.json()["code"]) == (409, "ai_key_missing")
    assert change.status_code == 404
    assert delete.status_code == 404
    for response in (activate, change, delete):
        assert USER_KEY not in response.text
    others = await UserRepository(db_session).get_by_id(other_user.id)
    assert others is not None and others.ai_provider is None
    # La de A sigue intacta y activa.
    key = await AiProviderKeyRepository(db_session).get(user.id, AiProvider.ANTHROPIC)
    assert key is not None and key.model == "claude-sonnet-5-5"
    owner = await UserRepository(db_session).get_by_id(user.id)
    assert owner is not None and owner.ai_provider == "anthropic"


@pytest.mark.asyncio
@pytest.mark.usefixtures("fakes")
@pytest.mark.parametrize(
    "body",
    [
        {"api_key": USER_KEY, "model": "m" * 101},
        {"api_key": USER_KEY, "model": 12345},
        {"api_key": USER_KEY, "model": "not-in-the-list"},
        {"api_key": USER_KEY + "x" * 600},
    ],
)
async def test_a_rejected_save_never_echoes_the_key(
    client: AsyncClient, body: dict[str, object]
):
    # Trampa de ia.md §7: un 422 de validación repite la entrada del campo que
    # falló. La clave nunca debe volver, aunque falle otro campo.
    response = await client.put(f"{KEYS}/anthropic", json=body)

    assert response.status_code == 422
    assert USER_KEY not in response.text
    assert "SECRET" not in response.text


# --- Cuota gratuita (RF-150: por cuenta, sin renovación) ----------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("fakes", "queue")
async def test_deleting_the_application_does_not_give_back_the_free_use(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_profile_entry(db_session, user.id, title="Backend", bullets=["SQL"])
    first = await make_application(db_session, user.id, job_description=JOB_DESCRIPTION)
    assert (await client.put(f"{CONSENTS}/groq")).status_code == 200
    requested = await client.post(proposals_url(first.id), json=CV)
    assert requested.status_code == 202
    # El worker la ejecutó y el proveedor respondió: el uso está gastado.
    proposal = await db_session.get(AiProposal, uuid.UUID(requested.json()["id"]))
    assert proposal is not None
    proposal.status = "invalid"
    proposal.error_code = "ai_response_invalid"
    proposal.billable = True
    await db_session.flush()

    deleted = await client.delete(f"/api/v1/applications/{first.id}")
    second = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )
    again = await client.post(proposals_url(second.id), json=CV)
    usage = (await client.get("/api/v1/me/usage")).json()

    assert deleted.status_code == 204
    by_key = {item["key"]: item for item in usage["limits"]}
    assert by_key["ai_cv_proposals"]["used"] == 1
    assert (again.status_code, again.json().get("code")) == (
        409,
        "ai_free_quota_exhausted",
    )
