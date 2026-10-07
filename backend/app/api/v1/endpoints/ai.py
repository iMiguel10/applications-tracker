import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.v1.deps import (
    enforce_ai_rate_limit,
    enforce_generate_rate_limit,
    get_ai_consent_service,
    get_ai_proposal_service,
    get_current_user,
    get_job_queue,
    require_verified_email,
)
from app.domain.ai import AiProvider
from app.infra.queue import JobQueue
from app.schemas.ai import (
    AiConsentsRead,
    AiProposalCreate,
    AiProposalDocumentCreate,
    AiProposalRead,
)
from app.schemas.common import ErrorResponse, error_responses
from app.schemas.document import DocumentRead
from app.schemas.user import CurrentUser
from app.services.ai_consent_service import AiConsentService
from app.services.ai_proposal_service import AiProposalService

proposals = APIRouter(prefix="/applications/{application_id}/ai-proposals", tags=["AI"])
consents = APIRouter(prefix="/ai/consents", tags=["AI"])


@proposals.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pedir una propuesta de CV adaptado a la oferta",
    responses=error_responses(404, 409, 422)
    | {
        403: {
            "model": ErrorResponse,
            "description": "`email_not_verified`: la IA exige el email verificado "
            "(salvo en una instalación sin correo).",
        },
    },
)
async def request_ai_proposal(
    application_id: uuid.UUID,
    data: AiProposalCreate,
    current_user: CurrentUser = Depends(require_verified_email),
    _rate_limit: None = Depends(enforce_ai_rate_limit),
    service: AiProposalService = Depends(get_ai_proposal_service),
    job_queue: JobQueue = Depends(get_job_queue),
) -> AiProposalRead:
    """Pide a la IA una propuesta de CV adaptado a la descripción de la oferta de
    la solicitud (RF-110): qué experiencias y logros destacar y en qué orden, cómo
    reformularlos, qué habilidades priorizar, un resumen y las carencias (RF-112).
    Responde enseguida con la propuesta en `queued`: consulta
    `GET /applications/{application_id}/ai-proposals/{proposal_id}` cada pocos
    segundos hasta que termine.

    Con la clave de la plataforma gasta un uso gratuito, también si la respuesta
    no pasa la validación (`invalid`) o la oferta no da para adaptar (`rejected`).

    Errores (409 salvo indicación): `ai_consent_required` (falta el
    consentimiento para el proveedor, `PUT /ai/consents/{provider}`),
    `job_description_missing`, `job_description_too_short` (422, con
    `min_length`), `profile_incomplete` (el perfil no tiene experiencia),
    `ai_free_quota_exhausted` (con `limit` y `used`), `ai_unavailable` (la
    instalación no tiene IA) y 429 `rate_limited` (5 por minuto y 50 al día)."""
    proposal = await service.request(current_user.id, application_id, data, job_queue)
    return AiProposalRead.model_validate(proposal)


@proposals.get(
    "",
    summary="Listar las propuestas de IA de una solicitud",
    responses=error_responses(404),
)
async def list_ai_proposals(
    application_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: AiProposalService = Depends(get_ai_proposal_service),
) -> list[AiProposalRead]:
    """Las últimas 20 propuestas de la solicitud, las más recientes primero."""
    items = await service.list(current_user.id, application_id)
    return [AiProposalRead.model_validate(item) for item in items]


@proposals.get(
    "/{proposal_id}",
    summary="Ver una propuesta de IA",
    responses=error_responses(404),
)
async def get_ai_proposal(
    application_id: uuid.UUID,
    proposal_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: AiProposalService = Depends(get_ai_proposal_service),
) -> AiProposalRead:
    """Una propuesta y su estado. En `succeeded`, la propuesta que se revisa antes
    de generar el PDF (RF-113): cada experiencia, logro y habilidad referencia por
    id un elemento del perfil."""
    proposal = await service.get(current_user.id, application_id, proposal_id)
    return AiProposalRead.model_validate(proposal)


@proposals.post(
    "/{proposal_id}/document",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generar el CV adaptado desde una propuesta revisada",
    responses=error_responses(404, 409, 422)
    | {
        403: {
            "model": ErrorResponse,
            "description": "`email_not_verified`: generar documentos exige el email "
            "verificado (salvo en una instalación sin correo).",
        },
    },
)
async def create_ai_proposal_document(
    application_id: uuid.UUID,
    proposal_id: uuid.UUID,
    data: AiProposalDocumentCreate,
    current_user: CurrentUser = Depends(require_verified_email),
    _rate_limit: None = Depends(enforce_generate_rate_limit),
    service: AiProposalService = Depends(get_ai_proposal_service),
    job_queue: JobQueue = Depends(get_job_queue),
) -> DocumentRead:
    """Genera en PDF el CV adaptado con la propuesta tal como queda tras revisarla
    (RF-113): el resumen y los logros reescritos, qué experiencias, logros y
    habilidades van y en qué orden. Puestos, empresas, fechas, formación y el
    resto salen del perfil actual (RF-111). Responde enseguida con el documento
    `ai_tailored` en `pending`, como al generar un CV; no vuelve a llamar a la
    IA ni gasta otro uso.

    409 `ai_proposal_not_ready` si la propuesta no terminó en `succeeded`, y
    `ai_proposal_outdated` si referencia algo que ya no está en el perfil (se
    editó después de pedirla): hay que pedir otra."""
    document = await service.create_document(
        current_user.id, application_id, proposal_id, data, job_queue
    )
    return DocumentRead.model_validate(document)


@consents.get("", summary="Ver los consentimientos para la IA")
async def get_ai_consents(
    current_user: CurrentUser = Depends(get_current_user),
    service: AiConsentService = Depends(get_ai_consent_service),
) -> AiConsentsRead:
    """A qué proveedor envía datos el uso gratuito de esta instalación y a qué
    proveedores ha dado el usuario su consentimiento (RF-116, RF-154)."""
    return await service.overview(current_user.id)


@consents.put(
    "/{provider}",
    summary="Dar el consentimiento para un proveedor de IA",
    responses=error_responses(422),
)
async def grant_ai_consent(
    provider: AiProvider,
    current_user: CurrentUser = Depends(get_current_user),
    service: AiConsentService = Depends(get_ai_consent_service),
) -> AiConsentsRead:
    """Acepta que los datos del perfil necesarios para adaptar el CV (nunca los de
    contacto) y la descripción de la oferta se envíen a `provider` (RF-116). Vale
    para la versión actual del texto: si cambia, hay que volver a darlo. 422
    `ai_provider_not_offered` si esta instalación no usa ese proveedor."""
    return await service.grant(current_user.id, provider)


@consents.delete(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retirar el consentimiento para un proveedor de IA",
)
async def revoke_ai_consent(
    provider: AiProvider,
    current_user: CurrentUser = Depends(get_current_user),
    service: AiConsentService = Depends(get_ai_consent_service),
) -> Response:
    """Desde ahora no se envía nada a `provider` (RF-116). Lo ya enviado y las
    propuestas hechas se quedan como están."""
    await service.revoke(current_user.id, provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
