"""API de la IA (F15): pedir y consultar propuestas de CV y los consentimientos.

La IA de la plataforma se configura aquí con un `Settings` propio (Groq), y los
services se sustituyen por los construidos con él. Ejecutar la propuesta (el
`worker`) se prueba en tests/services/test_ai_proposal_service.py.
"""

import uuid
from collections.abc import Callable, Iterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    get_ai_consent_service,
    get_ai_proposal_service,
    get_job_queue,
    get_limit_service,
)
from app.core.config import Settings, settings
from app.db.session import get_db
from app.infra.queue import InMemoryJobQueue
from app.infra.rate_limit import DisabledRateLimiter, LimitsRateLimiter
from app.main import app
from app.models.application import Application
from app.models.company import Company
from app.models.document import Document
from app.schemas.user import CurrentUser
from app.services.ai_consent_service import AiConsentService
from app.services.ai_proposal_service import AiProposalService
from app.services.limit_service import LimitService
from tests.auth_helpers import PASSWORD, form
from tests.factories import make_ai_proposal, make_application, make_profile_entry

MODEL = "openai/gpt-oss-120b"
PLATFORM_KEY = "gsk_platform_SECRET_api_tests"
CONFIG = Settings(
    **(
        settings.model_dump()
        | {
            "ai_platform_provider": "groq",
            "ai_platform_model": MODEL,
            "ai_platform_api_key": PLATFORM_KEY,
        }
    )
)
JOB_DESCRIPTION = "Backend con PostgreSQL y APIs REST. " * 10
CONSENTS = "/api/v1/ai/consents"
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
def platform(db_session: AsyncSession) -> Iterator[None]:
    """La instalación con IA de plataforma (Groq), sin llamar a nadie."""
    app.dependency_overrides[get_ai_proposal_service] = lambda: AiProposalService(
        db_session, CONFIG
    )
    app.dependency_overrides[get_ai_consent_service] = lambda: AiConsentService(
        db_session, CONFIG
    )
    # Con plataforma, GET /me/usage ofrece los usos gratuitos.
    app.dependency_overrides[get_limit_service] = lambda: LimitService(
        db_session, CONFIG
    )
    yield
    app.dependency_overrides.pop(get_limit_service, None)
    app.dependency_overrides.pop(get_ai_proposal_service, None)
    app.dependency_overrides.pop(get_ai_consent_service, None)


async def ready_application(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
) -> uuid.UUID:
    """Perfil con experiencia, consentimiento para Groq y una solicitud con oferta."""
    await make_profile_entry(db_session, user.id, title="Backend", bullets=["SQL"])
    application = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )
    assert (await client.put(f"{CONSENTS}/groq")).status_code == 200
    return application.id


# --- Consentimiento -----------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform")
async def test_consent_is_given_and_revoked_per_provider(client: AsyncClient):
    before = (await client.get(CONSENTS)).json()
    granted = await client.put(f"{CONSENTS}/groq")
    revoked = await client.delete(f"{CONSENTS}/groq")
    after = (await client.get(CONSENTS)).json()

    assert before == {
        "text_version": 1,
        "platform_provider": "groq",
        "platform_model": MODEL,
        "consents": [],
    }
    assert granted.status_code == 200
    [consent] = granted.json()["consents"]
    assert (consent["provider"], consent["granted"]) == ("groq", True)
    assert revoked.status_code == 204
    [consent] = after["consents"]
    assert consent["granted"] is False
    assert consent["revoked_at"] is not None


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform")
async def test_consent_to_a_provider_this_installation_does_not_use_is_refused(
    client: AsyncClient,
):
    response = await client.put(f"{CONSENTS}/openai")

    assert response.status_code == 422
    assert response.json()["code"] == "ai_provider_not_offered"


@pytest.mark.asyncio
async def test_the_consent_overview_never_shows_the_platform_key(
    client: AsyncClient, db_session: AsyncSession
):
    app.dependency_overrides[get_ai_consent_service] = lambda: AiConsentService(
        db_session, CONFIG
    )
    try:
        response = await client.get(CONSENTS)
    finally:
        app.dependency_overrides.pop(get_ai_consent_service, None)

    assert PLATFORM_KEY not in response.text


# --- Pedir una propuesta ------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform")
async def test_request_answers_202_with_the_queued_proposal(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    application_id = await ready_application(client, db_session, user)

    response = await client.post(proposals_url(application_id), json=CV)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert (body["kind"], body["language"], body["key_source"]) == (
        "cv",
        "es",
        "platform",
    )
    assert (body["provider"], body["model"]) == ("groq", MODEL)
    assert body["proposal"] is None
    assert PLATFORM_KEY not in response.text
    [job] = queue.jobs
    assert job.kwargs == {"proposal_id": body["id"], "user_id": str(user.id)}

    listing = await client.get(proposals_url(application_id))
    detail = await client.get(f"{proposals_url(application_id)}/{body['id']}")
    assert [item["id"] for item in listing.json()] == [body["id"]]
    assert detail.json()["id"] == body["id"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform", "queue")
async def test_the_second_request_has_no_free_use_left(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id = await ready_application(client, db_session, user)
    await client.post(proposals_url(application_id), json=CV)

    response = await client.post(proposals_url(application_id), json=CV)
    usage = (await client.get("/api/v1/me/usage")).json()

    assert response.status_code == 409
    assert response.json() | {"detail": ""} == {
        "detail": "",
        "code": "ai_free_quota_exhausted",
        "limit": 1,
        "used": 1,
    }
    by_key = {item["key"]: item for item in usage["limits"]}
    assert (by_key["ai_cv_proposals"]["used"], by_key["ai_cv_proposals"]["limit"]) == (
        1,
        1,
    )
    assert by_key["ai_cover_letter_proposals"]["used"] == 0


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform", "queue")
async def test_request_without_consent_is_refused(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    await make_profile_entry(db_session, user.id, title="Backend")
    application = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )

    response = await client.post(proposals_url(application.id), json=CV)

    assert response.status_code == 409
    assert response.json()["code"] == "ai_consent_required"


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform", "queue")
async def test_a_short_job_description_is_refused_before_spending(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id = await ready_application(client, db_session, user)
    short = await make_application(db_session, user.id, job_description="Backend.")

    response = await client.post(proposals_url(short.id), json=CV)
    usage = (await client.get("/api/v1/me/usage")).json()

    assert response.status_code == 422
    assert response.json()["code"] == "job_description_too_short"
    assert response.json()["min_length"] == 200
    by_key = {item["key"]: item for item in usage["limits"]}
    assert by_key["ai_cv_proposals"]["used"] == 0
    assert application_id


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform", "queue")
async def test_another_users_application_and_proposals_are_404(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    other_user: CurrentUser,
    as_user: Callable[[CurrentUser], None],
):
    application_id = await ready_application(client, db_session, user)
    proposal = (await client.post(proposals_url(application_id), json=CV)).json()

    as_user(other_user)
    requested = await client.post(proposals_url(application_id), json=CV)
    listing = await client.get(proposals_url(application_id))
    detail = await client.get(f"{proposals_url(application_id)}/{proposal['id']}")

    assert [requested.status_code, listing.status_code, detail.status_code] == [
        404,
        404,
        404,
    ]


@pytest.mark.asyncio
@pytest.mark.usefixtures("queue")
async def test_without_platform_ai_the_installation_has_no_ai(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # La configuración de pruebas no tiene AI_PLATFORM_PROVIDER.
    await make_profile_entry(db_session, user.id, title="Backend")
    application = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )

    response = await client.post(proposals_url(application.id), json=CV)
    consents = (await client.get(CONSENTS)).json()

    assert response.status_code == 409
    assert response.json()["code"] == "ai_unavailable"
    assert consents["platform_provider"] is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform", "queue")
async def test_requests_are_rate_limited_per_user(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    # 5 por minuto: la 6.ª espera, aunque las anteriores se rechazaran por cuota.
    application_id = await ready_application(client, db_session, user)
    app.state.rate_limiter = LimitsRateLimiter("async+memory://")
    try:
        for _ in range(5):
            assert (
                await client.post(proposals_url(application_id), json=CV)
            ).status_code in (
                202,
                409,
            )
        response = await client.post(proposals_url(application_id), json=CV)
    finally:
        app.state.rate_limiter = DisabledRateLimiter()

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"


# --- Verificación del email (contra el core real) ------------------------------


@pytest.mark.asyncio
async def test_an_unverified_email_cannot_request_a_proposal(
    real_auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    # La IA cuesta dinero: exige el email verificado (A38), con correo configurado.
    monkeypatch.setattr(settings, "smtp_host", "mailpit")
    signup = await real_auth_client.post(
        "/auth/signup",
        json=form(email=f"ai-{uuid.uuid4()}@example.com", password=PASSWORD),
        headers={"rid": "emailpassword"},
    )
    assert signup.json()["status"] == "OK"
    assert get_db in app.dependency_overrides

    response = await real_auth_client.post(proposals_url(uuid.uuid4()), json=CV)

    assert response.status_code == 403
    assert response.json()["code"] == "email_not_verified"


# --- Generar el CV adaptado (RF-113) ------------------------------------------


async def succeeded_proposal(
    db_session: AsyncSession, user: CurrentUser
) -> tuple[uuid.UUID, uuid.UUID, dict[str, object]]:
    """Una solicitud con una propuesta terminada sobre el perfil del usuario, y la
    propuesta revisada que se envía para generar el PDF."""
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
        "summary": "Revisado por mí",
        "experiences": [
            {
                "entry_id": str(entry.id),
                "bullets": [{"bullet_id": str(bullet.id), "text": "Optimicé SQL"}],
            }
        ],
        "skill_ids": [],
    }
    return application.id, proposal.id, reviewed


@pytest.mark.asyncio
async def test_a_reviewed_proposal_becomes_a_pending_tailored_cv(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    application_id, proposal_id, reviewed = await succeeded_proposal(db_session, user)

    response = await client.post(
        f"{proposals_url(application_id)}/{proposal_id}/document",
        json={"design": "modern", "proposal": reviewed},
    )

    assert response.status_code == 202
    body = response.json()
    assert (body["origin"], body["status"], body["kind"]) == (
        "ai_tailored",
        "pending",
        "cv",
    )
    assert (body["template"], body["language"]) == ("modern", "es")
    assert body["ai_proposal_id"] == str(proposal_id)
    assert body["name"] == "CV Backend Developer – " + body["name"].split(" – ")[1]
    document = await db_session.get(Document, uuid.UUID(body["id"]))
    assert document is not None and document.content is not None
    # Lo revisado por el usuario, no lo que propuso la IA.
    assert document.content["summary"] == "Revisado por mí"
    [section] = document.content["entry_sections"]
    assert section["entries"][0]["title"] == "Backend"
    assert section["entries"][0]["organization"] == "Acme"
    assert section["entries"][0]["bullets"][0]["text"] == "Optimicé SQL"
    [job] = queue.jobs
    assert job.job == "generate_document"


@pytest.mark.asyncio
@pytest.mark.usefixtures("queue")
async def test_a_proposal_referencing_what_is_no_longer_in_the_profile_is_outdated(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id, proposal_id, reviewed = await succeeded_proposal(db_session, user)
    reviewed["skill_ids"] = [str(uuid.uuid4())]

    response = await client.post(
        f"{proposals_url(application_id)}/{proposal_id}/document",
        json={"design": "modern", "proposal": reviewed},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ai_proposal_outdated"


@pytest.mark.asyncio
@pytest.mark.usefixtures("queue")
async def test_only_a_succeeded_proposal_can_become_a_cv(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id, _, reviewed = await succeeded_proposal(db_session, user)
    application = await db_session.get(Application, application_id)
    assert application is not None
    queued = await make_ai_proposal(db_session, application)

    response = await client.post(
        f"{proposals_url(application_id)}/{queued.id}/document",
        json={"design": "modern", "proposal": reviewed},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ai_proposal_not_ready"


@pytest.mark.asyncio
async def test_deleting_the_application_keeps_the_tailored_cv(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    application_id, proposal_id, reviewed = await succeeded_proposal(db_session, user)
    created = await client.post(
        f"{proposals_url(application_id)}/{proposal_id}/document",
        json={"design": "classic", "proposal": reviewed},
    )

    deleted = await client.delete(f"/api/v1/applications/{application_id}")
    document = await client.get(f"/api/v1/documents/{created.json()['id']}")

    assert deleted.status_code == 204
    assert document.status_code == 200
    # La propuesta sobrevive a su solicitud (registro de consumo, QA de F15), así
    # que el documento sigue diciendo con qué modelo y prompt se hizo (RF-115).
    assert document.json()["ai_proposal_id"] == str(proposal_id)
    assert queue.jobs


# --- La carta de presentación (RF-114) ----------------------------------------

LETTER = {
    "greeting": "Estimado equipo de Acme:",
    "paragraphs": ["Me presento al puesto.", "Optimicé SQL en Acme."],
    "closing": "Atentamente,",
}


async def succeeded_letter(
    db_session: AsyncSession, user: CurrentUser
) -> tuple[uuid.UUID, uuid.UUID]:
    entry = await make_profile_entry(
        db_session, user.id, title="Backend", bullets=["SQL"]
    )
    application = await make_application(
        db_session, user.id, job_description=JOB_DESCRIPTION
    )
    proposal = await make_ai_proposal(
        db_session,
        application,
        kind="cover_letter",
        prompt_version="cover_letter/v1",
        status="succeeded",
        billable=True,
        proposal={
            "greeting": "Hola:",
            "paragraphs": [
                {
                    "text": "Optimicé SQL.",
                    "sources": [{"kind": "bullet", "id": str(entry.bullets[0].id)}],
                }
            ],
            "closing": "Saludos,",
        },
    )
    return application.id, proposal.id


@pytest.mark.asyncio
@pytest.mark.usefixtures("platform", "queue")
async def test_a_letter_can_be_requested_after_the_cv(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id = await ready_application(client, db_session, user)
    cv = await client.post(proposals_url(application_id), json=CV)

    letter = await client.post(
        proposals_url(application_id), json={"kind": "cover_letter", "language": "en"}
    )
    usage = {
        item["key"]: item
        for item in (await client.get("/api/v1/me/usage")).json()["limits"]
    }

    assert (cv.status_code, letter.status_code) == (202, 202)
    assert (letter.json()["kind"], letter.json()["language"]) == ("cover_letter", "en")
    assert usage["ai_cover_letter_proposals"]["used"] == 1


@pytest.mark.asyncio
async def test_a_succeeded_letter_is_read_with_its_sources(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    application_id, proposal_id = await succeeded_letter(db_session, user)

    response = await client.get(f"{proposals_url(application_id)}/{proposal_id}")

    assert response.status_code == 200
    content = response.json()["proposal"]
    assert content["greeting"] == "Hola:"
    assert content["paragraphs"][0]["sources"][0]["kind"] == "bullet"


@pytest.mark.asyncio
async def test_a_reviewed_letter_becomes_a_pending_cover_letter(
    client: AsyncClient,
    db_session: AsyncSession,
    user: CurrentUser,
    queue: InMemoryJobQueue,
):
    application_id, proposal_id = await succeeded_letter(db_session, user)

    response = await client.post(
        f"{proposals_url(application_id)}/{proposal_id}/document",
        json={"design": "graphic", "letter": LETTER},
    )

    assert response.status_code == 202
    body = response.json()
    assert (body["kind"], body["origin"], body["status"]) == (
        "cover_letter",
        "ai_tailored",
        "pending",
    )
    assert body["name"].startswith("Carta Backend Developer – ")
    document = await db_session.get(Document, uuid.UUID(body["id"]))
    assert document is not None and document.content is not None
    application = await db_session.get(Application, application_id)
    assert application is not None
    # Lo revisado por el usuario; la empresa, el puesto y la fecha, de la aplicación.
    assert document.content["paragraphs"] == LETTER["paragraphs"]
    company = await db_session.get(Company, application.company_id)
    assert company is not None
    assert document.content["company"] == company.name
    assert document.content["position"] == application.position_title
    assert " de 20" in document.content["date"]
    [job] = queue.jobs
    assert job.job == "generate_document"


@pytest.mark.asyncio
@pytest.mark.usefixtures("queue")
async def test_the_content_must_match_the_proposal_kind(
    client: AsyncClient, db_session: AsyncSession, user: CurrentUser
):
    letter_app, letter_id = await succeeded_letter(db_session, user)
    cv_app, cv_id, reviewed = await succeeded_proposal(db_session, user)

    letter_as_cv = await client.post(
        f"{proposals_url(letter_app)}/{letter_id}/document",
        json={"design": "classic", "proposal": reviewed},
    )
    cv_as_letter = await client.post(
        f"{proposals_url(cv_app)}/{cv_id}/document",
        json={"design": "classic", "letter": LETTER},
    )
    both = await client.post(
        f"{proposals_url(cv_app)}/{cv_id}/document",
        json={"design": "classic", "letter": LETTER, "proposal": reviewed},
    )
    empty_paragraph = await client.post(
        f"{proposals_url(letter_app)}/{letter_id}/document",
        json={"design": "classic", "letter": LETTER | {"paragraphs": ["  "]}},
    )

    assert letter_as_cv.json()["code"] == "ai_document_mismatch"
    assert cv_as_letter.json()["code"] == "ai_document_mismatch"
    assert [
        r.status_code for r in (letter_as_cv, cv_as_letter, both, empty_paragraph)
    ] == [422] * 4
