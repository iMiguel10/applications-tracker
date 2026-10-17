"""Pruebas adversas de la IA en los services y el worker (F15, ia.md §10; v2 §8,
invariantes 13–15).

Un trabajo con el `user_id` de otro no toca la propuesta; la clave propia nunca
llega a los logs ni a la fila; una clave propia que no se puede usar nunca pasa a
la de la plataforma; el PDF de una propuesta válida lleva exactamente los puestos,
empresas y fechas del perfil (I3), aunque el modelo intente cambiarlos; y dos
barridos simultáneos del aviso de propuesta terminada reclaman un solo email.
"""

import asyncio
import io
import json
import logging
from datetime import UTC, date, datetime, timedelta

import pytest
from pypdf import PdfReader
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppException
from app.domain.ai import AiProvider, ProposalStatus
from app.domain.cv import CvSnapshot, format_period
from app.infra.crypto import generate_master_key
from app.infra.llm import LLMAuthError
from app.infra.llm.fake import FakeLLMProvider
from app.infra.pdf.designs import CvDesignCatalog
from app.infra.pdf.weasyprint_renderer import WeasyPrintRenderer
from app.infra.queue import InMemoryJobQueue
from app.models.ai_proposal import AiProposal
from app.models.notification_delivery import NotificationDelivery
from app.models.user import User
from app.repositories.profile_entry_repository import ProfileEntryRepository
from app.schemas.ai import AiProposalDocumentCreate
from app.schemas.user import CurrentUser
from app.services.ai_proposal_service import AiProposalService
from app.services.cv_render_service import CvRenderService
from app.services.notifications import AiProposalFinishedSweep
from tests.conftest import create_test_user, test_engine
from tests.factories import make_ai_proposal, make_application
from tests.services import test_ai_key_service as keyed
from tests.services.test_ai_proposal_notifications import FakeIdentities
from tests.services.test_ai_proposal_service import (
    prepare,
    requested,
    run,
    service,
    valid_output,
)

CATALOG = CvDesignCatalog()


# --- Aislamiento en el worker (B2 aplicado a la IA) --------------------------------


@pytest.mark.asyncio
async def test_a_job_with_another_users_id_does_not_touch_the_proposal(
    db_session: AsyncSession, user: CurrentUser, other_user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    proposal = await requested(db_session, user, application_id)
    fake = FakeLLMProvider()
    fake.reply(valid_output())

    await service(db_session, fake).run(other_user.id, proposal.id, datetime.now(UTC))
    await db_session.refresh(proposal)

    assert proposal.status == ProposalStatus.QUEUED
    assert proposal.started_at is None
    assert fake.calls == []


# --- La clave propia: nunca en logs ni en la fila (I7, invariante 15) -------------


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
async def test_the_own_key_never_reaches_the_logs_or_the_row(
    db_session: AsyncSession,
    user: CurrentUser,
    caplog: pytest.LogCaptureFixture,
    fails: bool,
) -> None:
    application_id = await keyed.prepared(db_session, user)
    fakes = keyed.providers()
    await keyed.keys(db_session, fakes).save(
        user.id, AiProvider.ANTHROPIC, keyed.USER_KEY, None
    )
    proposal = await keyed.proposals(db_session, fakes).request(
        user.id, application_id, keyed.CV, InMemoryJobQueue()
    )
    if fails:
        fakes[AiProvider.ANTHROPIC].fail(LLMAuthError(status_code=401))
    else:
        fakes[AiProvider.ANTHROPIC].reply(keyed.answer())

    with caplog.at_level(logging.DEBUG):
        await keyed.proposals(db_session, fakes).run(
            user.id, proposal.id, datetime.now(UTC)
        )
    await db_session.refresh(proposal)

    [call] = fakes[AiProvider.ANTHROPIC].calls
    assert call.api_key == keyed.USER_KEY
    assert keyed.USER_KEY not in caplog.text
    assert keyed.USER_KEY[-12:] not in caplog.text
    stored = json.dumps(
        {
            column.key: str(getattr(proposal, column.key))
            for column in proposal.__mapper__.c
        }
    )
    assert keyed.USER_KEY not in stored
    assert fakes[AiProvider.GROQ].calls == []


# --- Nunca a la clave de la plataforma (I4, invariante 14) ------------------------


@pytest.mark.asyncio
async def test_an_active_key_whose_provider_is_no_longer_offered_is_an_error(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await keyed.prepared(db_session, user)
    fakes = keyed.providers()
    await keyed.keys(db_session, fakes).save(
        user.id, AiProvider.ANTHROPIC, keyed.USER_KEY, None
    )
    # Quien despliega retira Anthropic: la clave activa ya no se puede usar.
    without_anthropic = Settings(
        **(keyed.CONFIG.model_dump() | {"ai_anthropic_models": ""})
    )

    with pytest.raises(AppException) as caught:
        await AiProposalService(db_session, without_anthropic, providers=fakes).request(
            user.id, application_id, keyed.CV, InMemoryJobQueue()
        )

    assert caught.value.code == "ai_key_unavailable"
    count = await db_session.scalar(
        select(func.count())
        .select_from(AiProposal)
        .where(AiProposal.user_id == user.id)
    )
    assert count == 0


@pytest.mark.asyncio
async def test_a_key_that_cannot_be_decrypted_fails_without_the_platform(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    # La clave maestra se retiró antes de rotar: la propuesta falla con
    # `ai_provider_auth`, sin facturar y sin tocar la clave de la plataforma.
    application_id = await keyed.prepared(db_session, user)
    fakes = keyed.providers()
    await keyed.keys(db_session, fakes).save(
        user.id, AiProvider.ANTHROPIC, keyed.USER_KEY, None
    )
    proposal = await keyed.proposals(db_session, fakes).request(
        user.id, application_id, keyed.CV, InMemoryJobQueue()
    )
    rotated = Settings(
        **(
            keyed.CONFIG.model_dump()
            | {"ai_keys_encryption_keys": generate_master_key()}
        )
    )

    await AiProposalService(db_session, rotated, providers=fakes).run(
        user.id, proposal.id, datetime.now(UTC)
    )
    await db_session.refresh(proposal)

    assert (proposal.status, proposal.error_code) == ("failed", "ai_provider_auth")
    assert (proposal.key_source, proposal.billable) == ("user", False)
    assert fakes[AiProvider.ANTHROPIC].calls == []
    assert fakes[AiProvider.GROQ].calls == []


# --- I3: el PDF lleva los hechos del perfil -------------------------------------


def _pdf_text(pdf: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf))
    return " ".join(" ".join(page.extract_text() for page in reader.pages).split())


@pytest.mark.asyncio
async def test_the_pdf_of_a_valid_proposal_has_exactly_the_profile_facts(
    db_session: AsyncSession, user: CurrentUser
) -> None:
    application_id = await prepare(db_session, user)
    [entry] = await ProfileEntryRepository(db_session).list(user.id)
    entry.organization = "Acme Ibérica"
    entry.start_date = date(2019, 3, 1)
    entry.end_date = date(2023, 6, 1)
    await db_session.commit()
    proposal = await requested(db_session, user, application_id)
    # El modelo intenta cambiar el puesto, la empresa y las fechas con campos que
    # el esquema no tiene: se ignoran, porque la propuesta no tiene dónde ponerlos.
    output = json.loads(valid_output())
    output["experiences"][0] |= {
        "title": "CTO",
        "organization": "Google",
        "start_date": "2001-01-01",
    }
    fake = FakeLLMProvider()
    fake.reply(json.dumps(output))

    proposal = await run(db_session, fake, proposal)
    assert proposal.status == ProposalStatus.SUCCEEDED
    assert proposal.proposal is not None
    reviewed = AiProposalDocumentCreate.model_validate(
        {
            "design": "modern",
            "proposal": {
                "summary": proposal.proposal["summary"],
                "experiences": proposal.proposal["experiences"],
                "skill_ids": proposal.proposal["skill_ids"],
            },
        }
    )
    document = await service(db_session).create_document(
        user.id, application_id, proposal.id, reviewed, InMemoryJobQueue()
    )
    assert document.content is not None
    snapshot = CvSnapshot.model_validate(document.content)
    pdf = await CvRenderService(WeasyPrintRenderer()).render(snapshot, "modern", "es")
    text = _pdf_text(pdf)

    [section] = snapshot.entry_sections
    [shown] = section.entries
    assert (shown.title, shown.organization) == ("Backend Developer", "Acme Ibérica")
    assert (shown.start_date, shown.end_date) == (date(2019, 3, 1), date(2023, 6, 1))
    period = format_period(shown, CATALOG.labels("es"))
    assert period is not None
    for fact in ("Backend Developer", "Acme Ibérica", " ".join(period.split())):
        assert fact in text
    for invented in ("CTO", "Google", "2001"):
        assert invented not in text


# --- I18: dos barridos a la vez, un solo aviso ------------------------------------

SWEEP_NOW = datetime(2033, 5, 2, 9, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_two_simultaneous_ai_proposal_sweeps_claim_a_single_email() -> None:
    async with AsyncSession(test_engine, expire_on_commit=False) as setup:
        owner = await create_test_user(setup)
        account = await setup.get(User, owner.id)
        assert account is not None
        account.notify_ai_proposal = True
        application = await make_application(setup, owner.id)
        await make_ai_proposal(
            setup,
            application,
            status="succeeded",
            proposal={"summary": "x"},
            finished_at=SWEEP_NOW - timedelta(minutes=3),
        )
        await setup.commit()
    session_a = AsyncSession(test_engine, expire_on_commit=False)
    session_b = AsyncSession(test_engine, expire_on_commit=False)
    queue_a, queue_b = InMemoryJobQueue(), InMemoryJobQueue()
    try:
        claimed = await asyncio.gather(
            AiProposalFinishedSweep(session_a, queue_a, FakeIdentities()).run(
                SWEEP_NOW
            ),
            AiProposalFinishedSweep(session_b, queue_b, FakeIdentities()).run(
                SWEEP_NOW
            ),
        )

        assert sorted(claimed) == [0, 1]
        assert len(queue_a.jobs) + len(queue_b.jobs) == 1
        async with AsyncSession(test_engine) as check:
            deliveries = await check.scalar(
                select(func.count())
                .select_from(NotificationDelivery)
                .where(NotificationDelivery.user_id == owner.id)
            )
        assert deliveries == 1
    finally:
        await session_a.close()
        await session_b.close()
        async with AsyncSession(test_engine) as cleanup:
            await cleanup.execute(delete(User).where(User.id == owner.id))
            await cleanup.commit()
