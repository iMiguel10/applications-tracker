import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.domain.ai import (
    CV_OUTPUT_MODELS,
    MAX_OUTPUT_TOKENS,
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
    InvalidProposalError,
    KeySource,
    OutdatedProposalError,
    ProposalErrorCode,
    ProposalStatus,
    apply_cv_proposal,
    build_cv_input,
    cost_micros,
    validate_cv_output,
    wrap_job_description,
)
from app.domain.cv import CvSelection
from app.domain.documents import DocumentOrigin
from app.domain.limits import LimitKey
from app.domain.profile import EntryKind
from app.infra.llm import (
    LLMError,
    LLMFinish,
    LLMInvalidOutputError,
    LLMProvider,
    LLMRequest,
    PlatformModel,
    platform_model,
    strict_json_schema,
)
from app.infra.llm.prompts import load_prompt
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
from app.services.ai_consent_service import AiConsentService
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
        if data.kind != AiTask.CV:
            # La carta llega en el paso 4 de F15.
            raise ConflictError("AI task not available", code="ai_task_unavailable")
        application = await self.applications.get(user_id, application_id)
        if application is None:
            raise NotFoundError("Application")

        platform = platform_model(self.config)
        if platform is None:
            # Sin uso gratuito; las claves propias llegan en el paso 5 de F15.
            raise ConflictError("AI not available", code="ai_unavailable")
        if not await self.consents.has_consent(user_id, platform.provider):
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

        # Cuota con la fila del usuario bloqueada (A30): cuenta lo facturado más
        # lo que está en curso, así que cinco peticiones a la vez con un uso
        # restante no pasan juntas (ia.md I5).
        await self.users.lock(user_id)
        await self.limits.check(user_id, LimitKey.AI_CV_PROPOSALS)

        proposal = await self.proposals.add(
            AiProposal(
                user_id=user_id,
                application_id=application.id,
                kind=data.kind.value,
                status=ProposalStatus.QUEUED.value,
                key_source=KeySource.PLATFORM.value,
                provider=platform.provider.value,
                model=platform.model,
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
    ) -> Document:
        """Genera el CV adaptado con la propuesta tal como la dejó el usuario tras
        revisarla (RF-113): la foto fija del perfil actual con la propuesta
        aplicada, maquetada como cualquier CV generado. No vuelve a llamar a la IA
        ni gasta otro uso: se pueden generar varios diseños de la misma propuesta.

        409 `ai_proposal_not_ready` si la propuesta no terminó bien y
        `ai_proposal_outdated` si referencia algo que ya no está en el perfil."""
        proposal = await self.get(user_id, application_id, proposal_id)
        if proposal.status != ProposalStatus.SUCCEEDED or proposal.kind != AiTask.CV:
            raise ConflictError(
                "The AI proposal is not ready", code="ai_proposal_not_ready"
            )
        design = resolve_design(
            self.cv_generation.catalog, data.design, proposal.language
        )
        base = await self.cv_generation.snapshot(user_id, CvSelection())
        try:
            snapshot = apply_cv_proposal(base, data.proposal.to_domain())
        except OutdatedProposalError as exc:
            logger.info("Propuesta %s desfasada: %s", proposal.id, exc)
            raise ConflictError(
                "The profile changed since the proposal", code="ai_proposal_outdated"
            ) from None

        application = await self.applications.get(user_id, application_id)
        assert application is not None  # get() ya lo comprobó con la propuesta
        return await self.cv_generation.create_pending(
            user_id,
            snapshot,
            design=design,
            language=proposal.language,
            name=data.name
            or f"CV {application.position_title} – {application.company.name}",
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
        platform = platform_model(self.config)
        adapter = self.providers.get(AiProvider(proposal.provider))
        if (
            adapter is None
            or platform is None
            or platform.provider != AiProvider(proposal.provider)
        ):
            # La configuración cambió entre pedirla y ejecutarla.
            return _failed(ProposalErrorCode.PROVIDER_UNAVAILABLE)

        application = await self.applications.get(user_id, proposal.application_id)
        profile = await self._profile(user_id)
        await self.session.commit()
        if application is None:
            # La solicitud se borró: `finish` no encontrará la fila.
            return _failed(ProposalErrorCode.PROVIDER_UNAVAILABLE)
        if not profile.experiences:
            return _failed(ProposalErrorCode.PROFILE_INCOMPLETE)

        profile_text, ids = build_cv_input(profile)
        # El esquema de la versión con que se pidió (A33): una propuesta en cola
        # al cambiar de versión se ejecuta con el prompt y el esquema de la suya.
        output_model = CV_OUTPUT_MODELS[proposal.prompt_version]
        request = LLMRequest(
            system=load_prompt(proposal.prompt_version, language=proposal.language),
            user=f"{profile_text}\n\n"
            f"{wrap_job_description(application.job_description or '')}",
            schema_name="cv_proposal",
            json_schema=strict_json_schema(output_model),
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
        try:
            response = await adapter.complete(
                request, model=proposal.model, api_key=platform.api_key
            )
        except LLMError as exc:
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
        billed = _billed(platform, response.input_tokens, response.output_tokens)
        if response.finish == LLMFinish.REFUSED:
            return billed | _invalid(ProposalErrorCode.RESPONSE_REFUSED)
        if response.finish == LLMFinish.TRUNCATED:
            logger.warning("Propuesta %s cortada por longitud", proposal.id)
            return billed | _invalid(ProposalErrorCode.RESPONSE_INVALID)
        try:
            output = output_model.model_validate_json(response.text)
        except ValidationError:
            logger.warning("Propuesta %s no cumple el esquema", proposal.id)
            return billed | _invalid(ProposalErrorCode.RESPONSE_INVALID)
        if output.insufficient_offer:
            return billed | {
                "status": ProposalStatus.REJECTED.value,
                "error_code": ProposalErrorCode.OFFER_INSUFFICIENT.value,
            }
        try:
            validated = validate_cv_output(output, ids)
        except InvalidProposalError as exc:
            # El motivo, sin texto del modelo ni del perfil.
            logger.warning("Propuesta %s inválida: %s", proposal.id, exc)
            return billed | _invalid(ProposalErrorCode.RESPONSE_INVALID)
        return billed | {
            "status": ProposalStatus.SUCCEEDED.value,
            "proposal": validated.model_dump(mode="json"),
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
    platform: PlatformModel, input_tokens: int, output_tokens: int
) -> dict[str, Any]:
    return {
        "billable": True,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_micros": cost_micros(
            input_tokens,
            output_tokens,
            platform.input_usd_per_mtok,
            platform.output_usd_per_mtok,
        ),
    }
