import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.v1.deps import (
    enforce_ai_rate_limit,
    enforce_generate_rate_limit,
    get_ai_consent_service,
    get_ai_key_service,
    get_ai_proposal_service,
    get_current_user,
    get_job_queue,
    require_verified_email,
)
from app.domain.ai import AiProvider
from app.infra.queue import JobQueue
from app.schemas.ai import (
    AiActiveProviderUpdate,
    AiConsentsRead,
    AiKeyModelUpdate,
    AiKeySave,
    AiKeysRead,
    AiProposalCreate,
    AiProposalDocumentCreate,
    AiProposalRead,
)
from app.schemas.common import ErrorResponse, error_responses
from app.schemas.document import DocumentRead
from app.schemas.user import CurrentUser
from app.services.ai_consent_service import AiConsentService
from app.services.ai_key_service import AiKeyService
from app.services.ai_proposal_service import AiProposalService

proposals = APIRouter(prefix="/applications/{application_id}/ai-proposals", tags=["AI"])
consents = APIRouter(prefix="/ai/consents", tags=["AI"])
keys = APIRouter(prefix="/ai/keys", tags=["AI"])


@proposals.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pedir una propuesta de CV adaptado o de carta de presentación",
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
    """Pide a la IA una propuesta para la oferta de la solicitud. Con `kind` `cv`,
    el CV adaptado (RF-110): qué experiencias y logros destacar y en qué orden,
    cómo reformularlos, qué habilidades priorizar, un resumen y los requisitos de
    la oferta (RF-112). Con `cover_letter`, la carta de presentación (RF-114):
    saludo, párrafos con las referencias al perfil en que se apoya cada uno y
    despedida. Responde enseguida con la propuesta en `queued`: consulta
    `GET /applications/{application_id}/ai-proposals/{proposal_id}` cada pocos
    segundos hasta que termine.

    Con la clave de la plataforma gasta un uso gratuito de ese tipo, también si la respuesta
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
    summary="Generar el CV adaptado o la carta desde una propuesta revisada",
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
    """Genera en PDF la propuesta tal como queda tras revisarla (RF-113), con un
    diseño de CV. Si es de `cv`, se envía `proposal`: el resumen y los logros
    reescritos, qué experiencias, logros y habilidades van y en qué orden;
    puestos, empresas, fechas, formación y el resto salen del perfil actual
    (RF-111). Si es de `cover_letter`, se envía `letter` (saludo, párrafos y
    despedida) y el documento es una carta (`kind` `cover_letter`) con el
    contacto del perfil, la empresa y el puesto de la solicitud y la fecha de hoy
    en la zona horaria del usuario. Responde enseguida con el documento
    `ai_tailored` en `pending`, como al generar un CV; no vuelve a llamar a la
    IA ni gasta otro uso.

    422 `ai_document_mismatch` si el contenido no es del tipo de la propuesta.
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


# --- Claves propias (RF-151, RF-153) ------------------------------------------


@keys.get("", summary="Ver las claves de IA propias")
async def get_ai_keys(
    current_user: CurrentUser = Depends(get_current_user),
    service: AiKeyService = Depends(get_ai_key_service),
) -> AiKeysRead:
    """Con qué proveedores y modelos se puede usar una clave propia en esta
    instalación, qué claves ha guardado el usuario (solo sus 4 últimos
    caracteres: la clave nunca se devuelve) y con cuál se usa la IA."""
    return await service.overview(current_user.id)


@keys.put(
    "/active",
    summary="Elegir con qué se usa la IA",
    responses=error_responses(409, 422),
)
async def set_active_ai_provider(
    data: AiActiveProviderUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: AiKeyService = Depends(get_ai_key_service),
) -> AiKeysRead:
    """Una clave propia guardada (`provider`) o, con `null`, los usos gratuitos de
    la plataforma. 409 `ai_key_missing` si no hay clave de ese proveedor."""
    return await service.set_active(current_user.id, data.provider)


@keys.put(
    "/{provider}",
    summary="Guardar una clave de IA propia",
    responses=error_responses(409, 422)
    | {
        503: {
            "model": ErrorResponse,
            "description": "`ai_provider_unavailable`: no se pudo comprobar la "
            "clave con el proveedor. Inténtalo más tarde.",
        },
    },
)
async def save_ai_key(
    provider: AiProvider,
    data: AiKeySave,
    current_user: CurrentUser = Depends(get_current_user),
    _rate_limit: None = Depends(enforce_ai_rate_limit),
    service: AiKeyService = Depends(get_ai_key_service),
) -> AiKeysRead:
    """Comprueba la clave con una llamada mínima al proveedor, sin generar texto
    (RF-153), la guarda cifrada y la deja como la que se usa. Sustituye la que
    hubiera de ese proveedor. Con clave propia no hay límite de usos: lo paga la
    cuenta del usuario en el proveedor.

    Errores (422): `ai_provider_not_offered`, `ai_model_not_allowed` (el modelo
    no está en `models`), `ai_key_invalid` (el proveedor la rechaza),
    `ai_model_unavailable` (la clave no tiene ese modelo) y `ai_provider_quota`
    (la cuenta del proveedor no tiene saldo); 409 `ai_keys_disabled` si la
    instalación no admite claves propias."""
    return await service.save(
        current_user.id, provider, data.api_key.get_secret_value(), data.model
    )


@keys.patch(
    "/{provider}",
    summary="Cambiar el modelo de una clave de IA propia",
    responses=error_responses(404, 409, 422),
)
async def change_ai_key_model(
    provider: AiProvider,
    data: AiKeyModelUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    _rate_limit: None = Depends(enforce_ai_rate_limit),
    service: AiKeyService = Depends(get_ai_key_service),
) -> AiKeysRead:
    """Otro modelo de la lista para la misma clave, comprobando con el proveedor
    que la clave lo tiene. Mismos errores que al guardarla."""
    return await service.change_model(current_user.id, provider, data.model)


@keys.delete(
    "/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar una clave de IA propia",
    responses=error_responses(404),
)
async def delete_ai_key(
    provider: AiProvider,
    current_user: CurrentUser = Depends(get_current_user),
    service: AiKeyService = Depends(get_ai_key_service),
) -> Response:
    """Borra la clave. Si era la que se usaba, se vuelve a los usos gratuitos. Las
    propuestas ya hechas con ella se quedan."""
    await service.delete(current_user.id, provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
