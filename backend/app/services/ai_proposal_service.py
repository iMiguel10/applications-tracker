import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.domain.ai import (
    MIN_JOB_DESCRIPTION_LENGTH,
    PROMPT_VERSIONS,
    QUEUED_GIVE_UP_AFTER,
    QUEUED_REQUEUE_AFTER,
    RUNNING_GRACE,
    SWEEP_BATCH,
    AiEntry,
    AiLanguage,
    AiProfile,
    AiProvider,
    AiSkill,
    AiTask,
    KeySource,
    OutdatedProposalError,
    ProposalErrorCode,
    ProposalStatus,
    apply_cv_proposal,
    cost_micros,
)
from app.domain.cover_letter import CoverLetterSnapshot
from app.domain.cv import CvSelection, CvSnapshot
from app.domain.dates import format_local_date
from app.domain.documents import DocumentOrigin
from app.domain.limits import LimitKey
from app.domain.profile import EntryKind
from app.domain.user import Language
from app.infra.llm import (
    LLMError,
    LLMInvalidOutputError,
    LLMProvider,
    PlatformModel,
    platform_model,
)
from app.infra.queue import JobQueue, QueueUnavailableError
from app.models.ai_proposal import AiProposal
from app.models.document import Document
from app.repositories.ai_proposal_repository import AiProposalRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.profile_entry_repository import ProfileEntryRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.profile_skill_repository import ProfileSkillRepository
from app.repositories.user_repository import UserRepository
from app.schemas.ai import AiProposalCreate, AiProposalDocumentCreate
from app.services.ai_call import interpret_response, prepare_call
from app.services.ai_consent_service import AiConsentService
from app.services.ai_key_service import AiKeyService
from app.services.cv_generation_service import CvGenerationService
from app.services.cv_render_service import resolve_design
from app.services.limit_service import LimitService

logger = logging.getLogger(__name__)

# El trabajo del `worker` que llama a la IA.
RUN_AI_PROPOSAL = "run_ai_proposal"
# Un solo intento, siempre: repetir una llamada que quizá ya se facturó la pagaría
# dos veces. Si se pierde, el barrido la cierra (segundo plano §2).
RUN_AI_PROPOSAL_MAX_ATTEMPTS = 1
# Cuántas propuestas de una solicitud devuelve el listado.
LIST_LIMIT = 20
# Nombre de una carta en la biblioteca si no se da otro, en el idioma de la carta.
LETTER_NAMES = {"es": "Carta", "en": "Cover letter"}
# La cuota gratuita de cada tarea (RF-150, decisión 0017).
QUOTA_KEYS = {
    AiTask.CV: LimitKey.AI_CV_PROPOSALS,
    AiTask.COVER_LETTER: LimitKey.AI_COVER_LETTER_PROPOSALS,
}


class AiProposalService:
    """Propuestas de IA para una solicitud (RF-110…119, flujo de v2 §5).

    Al pedirla se comprueban los requisitos y la cuota con la fila del usuario
    bloqueada (A30), se confirma la fila `queued` y, DESPUÉS del commit, se encola
    (invariante 11). El `worker` la toma, llama al proveedor y la valida (A32):
    `succeeded`, `invalid`, `rejected` o `failed`. El frontend consulta la fila
    mientras tanto (A35).

    Los adaptadores de los proveedores solo los necesita el `worker`.
    """

    def __init__(
        self,
        session: AsyncSession,
        config: Settings = settings,
        *,
        providers: Mapping[AiProvider, LLMProvider] | None = None,
    ) -> None:
        self.session = session
        self.config = config
        self.providers = providers or {}
        self.proposals = AiProposalRepository(session)
        self.applications = ApplicationRepository(session)
        self.profiles = ProfileRepository(session)
        self.entries = ProfileEntryRepository(session)
        self.skills = ProfileSkillRepository(session)
        self.users = UserRepository(session)
        self.limits = LimitService(session, config)
        self.consents = AiConsentService(session, config)
        self.cv_generation = CvGenerationService(session, config=config)
        self.own_keys = AiKeyService(session, config)

    # --- Pedir y consultar (API) --------------------------------------------

    async def request(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        data: AiProposalCreate,
        job_queue: JobQueue,
    ) -> AiProposal:
        """Crea la propuesta `queued` y la encola. La sesión, el email verificado y
        el rate limit los comprueba el endpoint."""
        application = await self.applications.get(user_id, application_id)
        if application is None:
            raise NotFoundError("Application")

        # Con qué se pide (ia.md §6): la clave propia activa o, si no hay, los usos
        # gratuitos. Una clave propia que no se puede usar es un error, nunca un
        # paso silencioso a la de la plataforma.
        own = await self.own_keys.active(user_id)
        if own is not None:
            key_source, provider, model = KeySource.USER, own.provider, own.model
        else:
            platform = platform_model(self.config)
            if platform is None:
                raise ConflictError("AI not available", code="ai_unavailable")
            key_source, provider, model = (
                KeySource.PLATFORM,
                platform.provider,
                platform.model,
            )
        if not await self.consents.has_consent(user_id, provider):
            raise ConflictError("AI consent required", code="ai_consent_required")

        description = (application.job_description or "").strip()
        if not description:
            raise ConflictError(
                "The application has no job description", code="job_description_missing"
            )
        if len(description) < MIN_JOB_DESCRIPTION_LENGTH:
            # RF-119: tan corta no da para un ajuste útil. Se dice antes de gastar
            # el uso, sin llamar a nadie.
            raise AppException(
                "The job description is too short",
                status_code=422,
                code="job_description_too_short",
                extra={"min_length": MIN_JOB_DESCRIPTION_LENGTH},
            )
        if not await self.entries.count(user_id, EntryKind.EXPERIENCE):
            raise ConflictError(
                "The profile has no experience", code="profile_incomplete"
            )

        if key_source == KeySource.PLATFORM:
            # Cuota con la fila del usuario bloqueada (A30): cuenta lo facturado
            # más lo que está en curso, así que cinco peticiones a la vez con un
            # uso restante no pasan juntas (ia.md I5). Con clave propia no hay
            # cuota: paga el usuario (0017).
            await self.users.lock(user_id)
            await self.limits.check(user_id, QUOTA_KEYS[data.kind])

        proposal = await self.proposals.add(
            AiProposal(
                user_id=user_id,
                application_id=application.id,
                kind=data.kind.value,
                status=ProposalStatus.QUEUED.value,
                key_source=key_source.value,
                provider=provider.value,
                model=model,
                prompt_version=PROMPT_VERSIONS[data.kind],
                language=data.language.value,
            )
        )
        await self.session.commit()
        await self.session.refresh(proposal)

        await self.enqueue(job_queue, proposal)
        return proposal

    async def enqueue(self, job_queue: JobQueue, proposal: AiProposal) -> None:
        """Encola una propuesta ya confirmada (invariante 11). Si la cola no
        responde, no falla: la fila sigue `queued` y el barrido la reencola."""
        try:
            await job_queue.enqueue(
                RUN_AI_PROPOSAL,
                # El tiempo de espera del proveedor más margen para la BD.
                timeout_seconds=int(self.config.ai_request_timeout_seconds) + 30,
                max_attempts=RUN_AI_PROPOSAL_MAX_ATTEMPTS,
                key=f"ai_proposal:{proposal.id}",
                proposal_id=str(proposal.id),
                user_id=str(proposal.user_id),
            )
        except QueueUnavailableError:
            logger.warning(
                "Propuesta %s sin encolar; la reencolará el barrido", proposal.id
            )

    async def list(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> Sequence[AiProposal]:
        if await self.applications.get(user_id, application_id) is None:
            raise NotFoundError("Application")
        return await self.proposals.list_for_application(
            user_id, application_id, LIST_LIMIT
        )

    async def get(
        self, user_id: uuid.UUID, application_id: uuid.UUID, proposal_id: uuid.UUID
    ) -> AiProposal:
        proposal = await self.proposals.get(user_id, application_id, proposal_id)
        if proposal is None:
            raise NotFoundError("AI proposal")
        return proposal

    async def create_document(
        self,
        user_id: uuid.UUID,
        application_id: uuid.UUID,
        proposal_id: uuid.UUID,
        data: AiProposalDocumentCreate,
        job_queue: JobQueue,
        now: datetime | None = None,
    ) -> Document:
        """Genera el CV adaptado o la carta con la propuesta tal como la dejó el
        usuario tras revisarla (RF-113, RF-114), maquetados como cualquier
        documento generado. No vuelve a llamar a la IA ni gasta otro uso: se pueden
        generar varios diseños de la misma propuesta.

        409 `ai_proposal_not_ready` si la propuesta no terminó bien y
        `ai_proposal_outdated` si referencia algo que ya no está en el perfil; 422
        `ai_document_mismatch` si el contenido no es del tipo de la propuesta."""
        proposal = await self.get(user_id, application_id, proposal_id)
        if proposal.status != ProposalStatus.SUCCEEDED:
            raise ConflictError(
                "The AI proposal is not ready", code="ai_proposal_not_ready"
            )
        letter = proposal.kind == AiTask.COVER_LETTER
        if (data.letter is not None) != letter:
            raise AppException(
                "The content does not match the proposal kind",
                status_code=422,
                code="ai_document_mismatch",
            )
        design = resolve_design(
            self.cv_generation.catalog, data.design, proposal.language
        )
        application = await self.applications.get(user_id, application_id)
        assert application is not None  # get() ya lo comprobó con la propuesta
        target = f"{application.position_title} – {application.company.name}"
        base = await self.cv_generation.snapshot(user_id, CvSelection())

        snapshot: CvSnapshot | CoverLetterSnapshot
        if data.letter is not None:
            # Nombre, contacto, empresa, puesto y fecha no salen de la IA: los pone
            # la aplicación. La fecha, el día de hoy en la zona del usuario.
            user = await self.users.get_by_id(user_id)
            snapshot = CoverLetterSnapshot(
                contact=base.contact,
                company=application.company.name,
                position=application.position_title,
                date=format_local_date(
                    now or datetime.now(UTC),
                    user.timezone if user else None,
                    Language(proposal.language),
                ),
                greeting=data.letter.greeting,
                paragraphs=list(data.letter.paragraphs),
                closing=data.letter.closing,
            )
            name = data.name or f"{LETTER_NAMES[proposal.language]} {target}"
        else:
            assert data.proposal is not None  # el schema exige uno de los dos
            try:
                snapshot = apply_cv_proposal(base, data.proposal.to_domain())
            except OutdatedProposalError as exc:
                logger.info("Propuesta %s desfasada: %s", proposal.id, exc)
                raise ConflictError(
                    "The profile changed since the proposal",
                    code="ai_proposal_outdated",
                ) from None
            name = data.name or f"CV {target}"

        return await self.cv_generation.create_pending(
            user_id,
            snapshot,
            design=design,
            language=proposal.language,
            name=name,
            origin=DocumentOrigin.AI_TAILORED,
            job_queue=job_queue,
            ai_proposal_id=proposal.id,
        )

    # --- Ejecutar (worker) --------------------------------------------------

    async def run(
        self, user_id: uuid.UUID, proposal_id: uuid.UUID, now: datetime
    ) -> None:
        """Toma la propuesta, llama al proveedor y la deja terminada (trabajo
        `run_ai_proposal`). Si ya no está en cola (otra ejecución la tomó, o se
        borró), no hace nada y no llama a nadie."""
        proposal = await self.proposals.claim(user_id, proposal_id, now)
        if proposal is None:
            await self.session.rollback()
            return
        await self.session.commit()

        outcome = await self._call(proposal)
        await self.proposals.finish(user_id, proposal_id, outcome)
        await self.session.commit()

    async def _call(self, proposal: AiProposal) -> dict[str, Any]:
        """Prepara la entrada, llama y valida. Devuelve las columnas del resultado.

        No guarda ninguna conexión ni bloqueo mientras espera al proveedor: lo leído
        se confirma antes de llamar y el resultado se escribe después con un UPDATE
        condicionado (`finish`)."""
        user_id = proposal.user_id
        provider = AiProvider(proposal.provider)
        adapter = self.providers.get(provider)
        platform = platform_model(self.config)
        api_key: str | None
        if proposal.key_source == KeySource.USER:
            # La clave del usuario, descifrada justo antes de llamar y solo en esta
            # variable (ia.md §7). Si la borró entre pedir y ejecutar, no se llama.
            api_key = await self.own_keys.decrypt(user_id, provider)
            if api_key is None:
                await self.session.commit()
                return _failed(ProposalErrorCode.PROVIDER_AUTH)
            prices = None
        elif platform is None or platform.provider != provider:
            # La configuración cambió entre pedirla y ejecutarla.
            return _failed(ProposalErrorCode.PROVIDER_UNAVAILABLE)
        else:
            api_key = platform.api_key
            prices = platform
        if adapter is None:
            return _failed(ProposalErrorCode.PROVIDER_UNAVAILABLE)

        application = (
            await self.applications.get(user_id, proposal.application_id)
            if proposal.application_id is not None
            else None
        )
        profile = await self._profile(user_id)
        await self.session.commit()
        if application is None:
            # La solicitud se borró: la propuesta queda sin ella y sin facturar.
            return _failed(ProposalErrorCode.PROVIDER_UNAVAILABLE)
        if not profile.experiences:
            return _failed(ProposalErrorCode.PROFILE_INCOMPLETE)

        call = prepare_call(
            profile,
            kind=AiTask(proposal.kind),
            prompt_version=proposal.prompt_version,
            language=proposal.language,
            job_description=application.job_description or "",
            position_title=application.position_title,
            company_name=application.company.name,
        )
        try:
            response = await adapter.complete(
                call.request, model=proposal.model, api_key=api_key
            )
        except LLMError as exc:
            # Solo el código: el mensaje del proveedor puede llevar la clave (ia.md §7).
            logger.warning(
                "Propuesta %s: el proveedor falló (%s)", proposal.id, exc.code
            )
            status = (
                ProposalStatus.INVALID
                if isinstance(exc, LLMInvalidOutputError)
                else ProposalStatus.FAILED
            )
            return {
                "status": status.value,
                "error_code": exc.code,
                "billable": exc.billable,
            }

        # Respondió: eso gasta el uso, pase o no la validación (ia.md §6, 0017).
        billed = _billed(prices, response.input_tokens, response.output_tokens)
        result = interpret_response(response, call)
        if result.reason:
            # El motivo, sin texto del modelo ni del perfil.
            logger.warning("Propuesta %s inválida: %s", proposal.id, result.reason)
        if result.status != ProposalStatus.SUCCEEDED:
            assert result.error_code is not None
            return billed | {
                "status": result.status.value,
                "error_code": result.error_code.value,
            }
        assert result.proposal is not None
        return billed | {
            "status": ProposalStatus.SUCCEEDED.value,
            "proposal": result.proposal.model_dump(mode="json"),
        }

    async def _profile(self, user_id: uuid.UUID) -> AiProfile:
        """Lo que la IA puede ver del perfil, sin datos de contacto (RNF-06)."""
        profile = await self.profiles.get(user_id)
        entries = await self.entries.list(user_id)
        skills = await self.skills.skills(user_id)
        languages = await self.skills.languages(user_id)
        return AiProfile(
            headline=profile.headline if profile else None,
            summary=profile.summary if profile else None,
            entries=[
                AiEntry(
                    id=entry.id,
                    kind=EntryKind(entry.kind),
                    title=entry.title,
                    organization=entry.organization,
                    start_date=entry.start_date,
                    end_date=entry.end_date,
                    is_current=entry.is_current,
                    description=entry.description,
                    bullets=[(bullet.id, bullet.text) for bullet in entry.bullets],
                )
                for entry in entries
            ],
            skills=[
                AiSkill(
                    id=skill.id,
                    name=skill.name,
                    category=skill.category,
                    level=skill.level,
                )
                for skill in skills
            ],
            languages=[
                AiLanguage(id=item.id, language=item.language, level=item.level)
                for item in languages
            ],
        )

    # --- Barrido (worker) ---------------------------------------------------

    async def sweep(self, job_queue: JobQueue, now: datetime) -> None:
        """Propuestas atascadas (como el barrido de documentos, segundo plano §3):
        las que siguen en cola se reencolan (su trabajo se perdió) o, pasada una
        hora, se dan por fallidas; las que llevan en curso más que el tiempo de
        espera del proveedor se dan por interrumpidas. Ninguna de las dos gasta el
        uso: no consta que el proveedor respondiera."""
        await self._sweep_queued(job_queue, now)
        hung_before = now - (
            timedelta(seconds=self.config.ai_request_timeout_seconds) + RUNNING_GRACE
        )
        after: tuple[datetime, uuid.UUID] | None = None
        while True:
            hung = await self.proposals.stale(
                ProposalStatus.RUNNING, hung_before, SWEEP_BATCH, after=after
            )
            if not hung:
                return
            assert hung[-1].started_at is not None
            after = (hung[-1].started_at, hung[-1].id)
            for proposal in hung:
                logger.error(
                    "Propuesta %s colgada: se da por interrumpida", proposal.id
                )
                proposal.status = ProposalStatus.FAILED.value
                proposal.error_code = ProposalErrorCode.INTERRUPTED.value
                proposal.finished_at = now
            await self.session.commit()
            if len(hung) < SWEEP_BATCH:
                return

    async def _sweep_queued(self, job_queue: JobQueue, now: datetime) -> None:
        requeue_before = now - QUEUED_REQUEUE_AFTER
        give_up_before = now - QUEUED_GIVE_UP_AFTER
        after: tuple[datetime, uuid.UUID] | None = None
        while True:
            stale = await self.proposals.stale(
                ProposalStatus.QUEUED, requeue_before, SWEEP_BATCH, after=after
            )
            if not stale:
                return
            after = (stale[-1].updated_at, stale[-1].id)
            requeue: list[AiProposal] = []
            for proposal in stale:
                if proposal.updated_at < give_up_before:
                    logger.error(
                        "Propuesta %s en cola más de una hora: se da por fallida",
                        proposal.id,
                    )
                    proposal.status = ProposalStatus.FAILED.value
                    proposal.error_code = ProposalErrorCode.INTERRUPTED.value
                    proposal.finished_at = now
                else:
                    requeue.append(proposal)
            await self.session.commit()
            for proposal in requeue:
                await self.enqueue(job_queue, proposal)
            if len(stale) < SWEEP_BATCH:
                return


def _failed(code: ProposalErrorCode) -> dict[str, Any]:
    """Falló antes de que el proveedor respondiera: no se factura."""
    return {"status": ProposalStatus.FAILED.value, "error_code": code.value}


def _invalid(code: ProposalErrorCode) -> dict[str, Any]:
    return {"status": ProposalStatus.INVALID.value, "error_code": code.value}


def _billed(
    prices: PlatformModel | None, input_tokens: int, output_tokens: int
) -> dict[str, Any]:
    """Respondió: se factura. El coste solo se estima con la plataforma, que tiene
    precios configurados; con una clave propia lo paga el usuario y a la plataforma no le cuesta nada."""
    return {
        "billable": True,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_micros": cost_micros(
            input_tokens,
            output_tokens,
            prices.input_usd_per_mtok,
            prices.output_usd_per_mtok,
        )
        if prices
        else 0,
    }
