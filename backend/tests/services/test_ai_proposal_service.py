"""`AiProposalService` con un proveedor simulado (RNF-23, ia.md §10).

Ninguna prueba llama a un proveedor. Las respuestas grabadas cubren lo que la
validación tiene que parar: referencias inventadas, esquema roto, oferta
insuficiente, errores del proveedor con la clave dentro…
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import AppException, LimitReachedError
from app.domain.ai import AiProvider, AiTask, ProposalLanguage, ProposalStatus
from app.domain.limits import LimitKey
from app.infra.llm import (
    LLMAuthError,
    LLMFinish,
    LLMInvalidOutputError,
    LLMUnavailableError,
)
from app.infra.llm.fake import FakeLLMProvider
from app.infra.queue import InMemoryJobQueue
from app.models.ai_proposal import AiProposal
from app.models.profile_skill import ProfileSkill
from app.repositories.ai_consent_repository import AiConsentRepository
from app.repositories.profile_entry_repository import ProfileEntryRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai import AiProposalCreate
from app.schemas.user import CurrentUser
from app.services.ai_proposal_service import RUN_AI_PROPOSAL, AiProposalService
from app.services.limit_service import LimitService
from tests.conftest import create_test_user, test_engine
from tests.factories import make_application, make_profile_entry

PLATFORM_KEY = "gsk_platform_SECRET_0123456789"
MODEL = "openai/gpt-oss-120b"
CONFIG = Settings(
    **(
        settings.model_dump()
        | {
            "ai_platform_provider": "groq",
            "ai_platform_model": MODEL,
            "ai_platform_api_key": PLATFORM_KEY,
            "ai_platform_input_usd_per_mtok": 0.15,
            "ai_platform_output_usd_per_mtok": 0.60,
        }
    )
)
JOB_DESCRIPTION = (
    "Buscamos backend developer con experiencia en PostgreSQL, APIs REST y "
    "Kubernetes. Valoramos tests automáticos, revisiones de código y trabajo en "
    "equipo. Remoto en Europa, jornada completa, contrato indefinido."
)
CV = AiProposalCreate(kind=AiTask.CV, language=ProposalLanguage.ES)


def valid_output(**changes: Any) -> str:
    values: dict[str, Any] = {
        "insufficient_offer": False,
        "requirements": [
            {
                "requirement": "PostgreSQL",
                "importance": "required",
                "keywords": ["PostgreSQL", "Postgres"],
                "evidence": ["s1", "e1.b1"],
                "note": "",
            },
            {
                "requirement": "Kubernetes",
                "importance": "preferred",
                "keywords": ["Kubernetes", "K8s"],
                "evidence": [],
                "note": "No aparece en el perfil",
            },
        ],
        "summary": "Backend con PostgreSQL y APIs.",
        "experiences": [
            {
                "entry_id": "e1",
                "bullets": [{"bullet_id": "e1.b1", "text": "Diseñé APIs REST"}],
            }
        ],
        "skills": ["s1"],
    } | changes
    return json.dumps(values)


async def prepare(session: AsyncSession, user: CurrentUser) -> uuid.UUID:
    """Solicitud con oferta, perfil con contacto, experiencia, logro y habilidad, y
    el consentimiento para Groq. Devuelve el id de la solicitud."""
    profile = await ProfileRepository(session).get_or_create(user.id)
    profile.full_name = "Ana Pérez Contacto"
    profile.contact_email = "ana.contacto@example.com"
    profile.phone = "+34 600 111 222"
    profile.location = "Calle Secreta 1"
    profile.links = [{"label": "Web", "url": "https://ana-secreta.example.com"}]
    await ProfileRepository(session).save(profile)
    await make_profile_entry(
        session, user.id, title="Backend Developer", bullets=["APIs con FastAPI"]
    )
    session.add(ProfileSkill(profile_id=profile.id, name="PostgreSQL", position=0))
    await session.flush()
    await AiConsentRepository(session).grant(
        user.id, AiProvider.GROQ, 1, datetime.now(UTC)
    )
    application = await make_application(
        session, user.id, job_description=JOB_DESCRIPTION
    )
    await session.commit()
    return application.id


def service(
    session: AsyncSession,
    fake: FakeLLMProvider | None = None,
    config: Settings = CONFIG,
) -> AiProposalService:
    providers = {AiProvider.GROQ: fake} if fake is not None else None
    return AiProposalService(session, config, providers=providers)


async def requested(
    session: AsyncSession, user: CurrentUser, application_id: uuid.UUID
) -> AiProposal:
    return await service(session).request(
        user.id, application_id, CV, InMemoryJobQueue()
    )


async def run(
    session: AsyncSession, fake: FakeLLMProvider, proposal: AiProposal
) -> AiProposal:
    await service(session, fake).run(proposal.user_id, proposal.id, datetime.now(UTC))
    await session.refresh(proposal)
    return proposal


# --- Pedirla -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_queues_a_platform_proposal_and_enqueues_only_ids(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    queue = InMemoryJobQueue()

    proposal = await service(db_session).request(user.id, application_id, CV, queue)

    assert proposal.status == ProposalStatus.QUEUED
    assert (proposal.provider, proposal.model) == ("groq", MODEL)
    assert (proposal.key_source, proposal.prompt_version) == ("platform", "cv/v2")
    [job] = queue.jobs
    assert job.job == RUN_AI_PROPOSAL
    assert job.max_attempts == 1
    # Un trabajo nunca lleva la clave: Valkey guarda los trabajos en disco.
    assert job.kwargs == {"proposal_id": str(proposal.id), "user_id": str(user.id)}


@pytest.mark.asyncio
async def test_the_requirements_have_stable_codes(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    application = await make_application(db_session, user.id, job_description="Corta")
    empty = await make_application(db_session, user.id)
    await db_session.commit()
    # Los ids antes de nada: cada rollback caduca los objetos de la sesión.
    short_id, empty_id = application.id, empty.id

    async def code_of(app_id: uuid.UUID, config: Settings = CONFIG) -> str:
        with pytest.raises(AppException) as caught:
            await service(db_session, config=config).request(
                user.id, app_id, CV, InMemoryJobQueue()
            )
        await db_session.rollback()
        return caught.value.code

    assert await code_of(short_id) == "job_description_too_short"
    assert await code_of(empty_id) == "job_description_missing"
    assert await code_of(uuid.uuid4()) == "not_found"
    no_platform = Settings(**(settings.model_dump() | {"ai_platform_provider": None}))
    assert await code_of(application_id, no_platform) == "ai_unavailable"


@pytest.mark.asyncio
async def test_without_consent_nothing_is_queued(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # I11.
    application_id = await prepare(db_session, user)
    await AiConsentRepository(db_session).revoke(
        user.id, AiProvider.GROQ, datetime.now(UTC)
    )
    queue = InMemoryJobQueue()

    with pytest.raises(AppException) as caught:
        await service(db_session).request(user.id, application_id, CV, queue)

    assert caught.value.code == "ai_consent_required"
    assert queue.jobs == []


@pytest.mark.asyncio
async def test_without_experience_the_profile_is_incomplete(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    await AiConsentRepository(db_session).grant(
        user.id, AiProvider.GROQ, 1, datetime.now(UTC)
    )
    application = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )

    with pytest.raises(AppException) as caught:
        await requested(db_session, user, application.id)

    assert caught.value.code == "profile_incomplete"


@pytest.mark.asyncio
async def test_a_queued_proposal_already_counts_against_the_free_use(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # Lo que está en curso cuenta: si no, varias peticiones a la vez pasarían.
    application_id = await prepare(db_session, user)
    await requested(db_session, user, application_id)

    with pytest.raises(LimitReachedError) as caught:
        await requested(db_session, user, application_id)

    assert caught.value.code == "ai_free_quota_exhausted"
    assert caught.value.extra == {"limit": 1, "used": 1}


@pytest.mark.asyncio
async def test_with_unlimited_free_uses_the_quota_never_runs_out(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # LIMIT_AI_CV_PROPOSALS=unlimited (0020): las propuestas siguen contando como
    # uso de la plataforma, pero ninguna se rechaza por cuota.
    unlimited = Settings(**(CONFIG.model_dump() | {"limit_ai_cv_proposals": None}))
    application_id = await prepare(db_session, user)

    for _ in range(3):
        await service(db_session, config=unlimited).request(
            user.id, application_id, CV, InMemoryJobQueue()
        )

    usage = await LimitService(db_session, unlimited).usage(user.id)
    cv = next(item for item in usage if item.key == LimitKey.AI_CV_PROPOSALS)
    assert (cv.used, cv.limit, cv.remaining) == (3, None, None)


# --- Ejecutarla ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_valid_answer_succeeds_with_real_ids_cost_and_usage(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.reply(valid_output(), input_tokens=5_000, output_tokens=2_500)

    proposal = await run(db_session, fake, proposal)

    assert proposal.status == ProposalStatus.SUCCEEDED
    assert proposal.billable is True
    assert (proposal.input_tokens, proposal.output_tokens) == (5_000, 2_500)
    assert proposal.cost_micros == 2_250
    assert proposal.error_code is None
    assert proposal.proposal is not None
    [experience] = proposal.proposal["experiences"]
    profile_entries = await ProfileEntryRepository(db_session).list(user.id)
    assert experience["entry_id"] == str(profile_entries[0].id)
    assert experience["bullets"][0]["text"] == "Diseñé APIs REST"
    # Los requisitos, con la evidencia en UUID reales; las carencias salen de ellos.
    postgres, kubernetes = proposal.proposal["requirements"]
    assert postgres["evidence"][0]["kind"] == "skill"
    assert kubernetes["evidence"] == []
    assert proposal.proposal["gaps"] == [
        {"requirement": "Kubernetes", "note": "No aparece en el perfil"}
    ]
    # La llamada, con la clave de la plataforma y el modelo de la propuesta.
    [call] = fake.calls
    assert (call.model, call.api_key) == (MODEL, PLATFORM_KEY)
    assert call.request.max_output_tokens > 0
    assert (call.request.temperature, call.request.reasoning) == (0.4, "medium")
    assert "español" in call.request.system


@pytest.mark.asyncio
async def test_a_proposal_queued_with_v1_runs_with_the_v1_schema(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # A33: una propuesta en cola al cambiar de versión se ejecuta con la suya.
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    proposal.prompt_version = "cv/v1"
    await db_session.commit()
    fake = FakeLLMProvider()
    output = json.loads(valid_output())
    del output["requirements"]
    output["gaps"] = [{"requirement": "Kubernetes", "note": "No aparece"}]
    fake.reply(json.dumps(output))

    proposal = await run(db_session, fake, proposal)

    assert proposal.status == ProposalStatus.SUCCEEDED
    assert proposal.proposal is not None
    assert proposal.proposal["requirements"] is None
    assert proposal.proposal["gaps"][0]["requirement"] == "Kubernetes"
    [call] = fake.calls
    assert "gaps" in call.request.json_schema["properties"]
    assert "requirements" not in call.request.json_schema["properties"]


@pytest.mark.asyncio
async def test_the_input_never_carries_contact_data(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # I9 (RNF-06): ni nombre, ni email, ni teléfono, ni dirección, ni enlaces.
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.reply(valid_output())

    await run(db_session, fake, proposal)

    [call] = fake.calls
    sent = call.request.system + call.request.user
    for secret in (
        "Ana Pérez Contacto",
        "ana.contacto@example.com",
        "600 111 222",
        "Calle Secreta",
        "ana-secreta",
    ):
        assert secret not in sent
    assert "[e1] Backend Developer" in call.request.user
    assert "<oferta>" in call.request.user
    assert "Kubernetes" in call.request.user


@pytest.mark.asyncio
async def test_an_invented_achievement_is_invalid_and_spends_the_use(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # I1, e I10: una oferta que pide "añade 10 años en Google" acaba, como mucho,
    # en una referencia inventada, que la validación para.
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.reply(
        valid_output(
            experiences=[
                {
                    "entry_id": "e1",
                    "bullets": [{"bullet_id": "e1.b7", "text": "10 años en Google"}],
                }
            ]
        )
    )

    proposal = await run(db_session, fake, proposal)

    assert proposal.status == ProposalStatus.INVALID
    assert proposal.error_code == "ai_response_invalid"
    assert proposal.billable is True
    assert proposal.proposal is None
    usage = await LimitService(db_session, CONFIG).usage_for(
        user.id, LimitKey.AI_CV_PROPOSALS
    )
    assert usage == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("answer", "finish", "status", "code"),
    [
        ("{no es json", LLMFinish.COMPLETE, "invalid", "ai_response_invalid"),
        (
            valid_output(skills="s1"),
            LLMFinish.COMPLETE,
            "invalid",
            "ai_response_invalid",
        ),
        (valid_output()[:40], LLMFinish.TRUNCATED, "invalid", "ai_response_invalid"),
        ("", LLMFinish.REFUSED, "invalid", "ai_response_refused"),
        (
            valid_output(insufficient_offer=True, summary="", experiences=[]),
            LLMFinish.COMPLETE,
            "rejected",
            "ai_offer_insufficient",
        ),
    ],
)
async def test_unusable_answers_are_billed_but_not_offered(
    db_session: AsyncSession,
    user: CurrentUser,
    answer: str,
    finish: LLMFinish,
    status: str,
    code: str,
) -> None:
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.reply(answer, finish=finish)

    proposal = await run(db_session, fake, proposal)

    assert (proposal.status, proposal.error_code) == (status, code)
    assert proposal.billable is True
    assert proposal.proposal is None


@pytest.mark.asyncio
async def test_a_failure_before_any_answer_frees_the_use(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # I6: un fallo al conectar no se factura y no gasta el uso: se puede volver a
    # pedir. Uno que el proveedor sí generó (esquema roto) sí lo gasta.
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.fail(LLMUnavailableError())

    proposal = await run(db_session, fake, proposal)

    assert (proposal.status, proposal.error_code) == (
        "failed",
        "ai_provider_unavailable",
    )
    assert proposal.billable is False
    second = await requested(db_session, user, application_id)
    fake.fail(LLMInvalidOutputError(status_code=400))
    second = await run(db_session, fake, second)
    assert (second.status, second.billable) == ("invalid", True)
    with pytest.raises(LimitReachedError):
        await requested(db_session, user, application_id)


@pytest.mark.asyncio
async def test_a_provider_error_never_stores_the_key(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # I7: la fila guarda solo el código, nunca el texto del proveedor ni la clave.
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.fail(LLMAuthError(status_code=401))

    proposal = await run(db_session, fake, proposal)

    assert proposal.error_code == "ai_provider_auth"
    stored = json.dumps(
        {
            column.key: str(getattr(proposal, column.key))
            for column in proposal.__mapper__.c
        }
    )
    assert PLATFORM_KEY not in stored


@pytest.mark.asyncio
async def test_a_proposal_runs_only_once(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # SAQ puede relanzar un trabajo: la segunda ejecución no llama al proveedor,
    # que facturaría dos veces.
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.reply(valid_output())

    await run(db_session, fake, proposal)
    await run(db_session, fake, proposal)

    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_a_profile_emptied_before_running_is_incomplete_and_not_billed(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    for entry in await ProfileEntryRepository(db_session).list(user.id):
        await db_session.delete(entry)
    await db_session.commit()
    fake = FakeLLMProvider()

    proposal = await run(db_session, fake, proposal)

    assert (proposal.status, proposal.error_code) == ("failed", "profile_incomplete")
    assert proposal.billable is False
    assert fake.calls == []


# --- Barrido ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_sweep_requeues_lost_jobs_and_closes_hung_ones(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    lost = await requested(db_session, user, application_id)
    await LimitService(db_session, CONFIG).set_override(
        user.id, LimitKey.AI_CV_PROPOSALS, 10
    )
    hung = await requested(db_session, user, application_id)
    abandoned = await requested(db_session, user, application_id)
    now = datetime.now(UTC)
    hung.status = ProposalStatus.RUNNING.value
    hung.started_at = now - timedelta(hours=1)
    await db_session.commit()
    queue = InMemoryJobQueue()

    # Diez minutos después, la perdida se reencola.
    await service(db_session).sweep(queue, now + timedelta(minutes=10))
    assert {job.kwargs["proposal_id"] for job in queue.jobs} == {
        str(lost.id),
        str(abandoned.id),
    }
    await db_session.refresh(hung)
    assert (hung.status, hung.error_code) == ("failed", "ai_interrupted")
    assert hung.billable is False

    # Dos horas después, las que siguen en cola se dan por fallidas.
    await service(db_session).sweep(InMemoryJobQueue(), now + timedelta(hours=2))
    await db_session.refresh(lost)
    assert (lost.status, lost.error_code) == ("failed", "ai_interrupted")


# --- Carreras con transacciones reales ----------------------------------------


@pytest.mark.asyncio
async def test_simultaneous_requests_with_one_free_use_queue_only_one() -> None:
    # I5 (A30): con la fila del usuario bloqueada, solo una pasa.
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        application_id = await prepare(setup, owner)
    sessions = [AsyncSession(test_engine, expire_on_commit=False) for _ in range(5)]

    async def ask(session: AsyncSession) -> str:
        try:
            await requested(session, owner, application_id)
        except AppException as exc:
            await session.rollback()
            return exc.code
        return "ok"

    try:
        results = await asyncio.gather(*(ask(session) for session in sessions))

        assert sorted(results) == ["ai_free_quota_exhausted"] * 4 + ["ok"]
    finally:
        for session in sessions:
            await session.close()
        async with AsyncSession(test_engine) as cleanup:
            await UserRepository(cleanup).delete(owner.id)
            await cleanup.commit()


# --- La carta de presentación (RF-114) ---------------------------------------

LETTER = AiProposalCreate(kind=AiTask.COVER_LETTER, language=ProposalLanguage.ES)


def letter_output(**changes: Any) -> str:
    values: dict[str, Any] = {
        "insufficient_offer": False,
        "greeting": "Estimado equipo de Acme:",
        "paragraphs": [
            {"text": "Me presento al puesto de backend.", "sources": []},
            {"text": "Diseñé APIs con FastAPI.", "sources": ["e1.b1", "s1"]},
        ],
        "closing": "Atentamente,",
    } | changes
    return json.dumps(values)


@pytest.mark.asyncio
async def test_the_letter_has_its_own_free_use_and_prompt(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # Gastar la del CV no gasta la de la carta (decisión 0017), y al revés.
    application_id = await prepare(db_session, user)
    await requested(db_session, user, application_id)

    letter = await service(db_session).request(
        user.id, application_id, LETTER, InMemoryJobQueue()
    )

    assert (letter.kind, letter.prompt_version) == ("cover_letter", "cover_letter/v1")
    with pytest.raises(LimitReachedError) as caught:
        await service(db_session).request(
            user.id, application_id, LETTER, InMemoryJobQueue()
        )
    assert caught.value.code == "ai_free_quota_exhausted"


@pytest.mark.asyncio
async def test_a_valid_letter_succeeds_with_its_sources_as_real_ids(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    proposal = await service(db_session).request(
        user.id, application_id, LETTER, InMemoryJobQueue()
    )
    fake = FakeLLMProvider()
    fake.reply(letter_output())

    proposal = await run(db_session, fake, proposal)

    assert proposal.status == ProposalStatus.SUCCEEDED
    assert proposal.proposal is not None
    opening, job = proposal.proposal["paragraphs"]
    assert opening["sources"] == []
    [entry] = await ProfileEntryRepository(db_session).list(user.id)
    assert job["sources"][0] == {"kind": "bullet", "id": str(entry.bullets[0].id)}
    assert job["sources"][1]["kind"] == "skill"
    [call] = fake.calls
    assert call.request.schema_name == "cover_letter"
    # La carta razona más que el CV: con `medium`, Groq adornaba más (ia.md §9).
    assert call.request.reasoning == "high"
    assert "paragraphs" in call.request.json_schema["properties"]
    # El puesto y la empresa, delimitados; el contacto, nunca (I9).
    assert "<solicitud>" in call.request.user
    assert "Puesto: " in call.request.user
    for secret in ("Ana Pérez Contacto", "ana.contacto@example.com", "600 111 222"):
        assert secret not in call.request.user + call.request.system


@pytest.mark.asyncio
async def test_a_letter_citing_what_is_not_in_the_profile_is_invalid(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    proposal = await service(db_session).request(
        user.id, application_id, LETTER, InMemoryJobQueue()
    )
    fake = FakeLLMProvider()
    fake.reply(
        letter_output(
            paragraphs=[{"text": "Diez años en Google.", "sources": ["e7.b1"]}]
        )
    )

    proposal = await run(db_session, fake, proposal)

    assert proposal.status == ProposalStatus.INVALID
    assert proposal.error_code == "ai_response_invalid"
    assert proposal.billable is True
    assert proposal.proposal is None
