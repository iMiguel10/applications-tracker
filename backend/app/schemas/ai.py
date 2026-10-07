import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.ai import (
    AI_CONSENT_VERSION,
    AiProvider,
    AiTask,
    CvProposal,
    KeySource,
    ProposalErrorCode,
    ProposalLanguage,
    ProposalStatus,
)


class AiProposalCreate(BaseModel):
    kind: AiTask = Field(
        description="`cv` (adaptar el CV, RF-110). `cover_letter` llega en un paso "
        "posterior de F15."
    )
    language: ProposalLanguage = Field(
        description="Idioma en que se escriben el resumen, los logros y las carencias."
    )


class AiProposalRead(BaseModel):
    """Un uso de la IA y, si salió bien, la propuesta que se revisa (RF-113)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    kind: AiTask
    status: ProposalStatus = Field(
        description="`queued` y `running` mientras se genera: consulta "
        "`GET .../ai-proposals/{proposal_id}` cada pocos segundos. Termina en "
        "`succeeded` (con `proposal`), `invalid` (la respuesta no pasó la "
        "validación), `rejected` (la oferta no da para adaptar, RF-119) o `failed`."
    )
    language: ProposalLanguage
    key_source: KeySource = Field(
        description="`platform`: un uso gratuito. `user`: la clave propia del usuario."
    )
    provider: AiProvider
    model: str = Field(examples=["openai/gpt-oss-120b"])
    error_code: ProposalErrorCode | None = Field(
        description="Solo en `invalid`, `rejected` y `failed`: por qué no salió."
    )
    proposal: CvProposal | None = Field(
        description="Solo en `succeeded`. Cada experiencia, logro y habilidad "
        "referencia por id un elemento del perfil; los puestos, empresas y fechas "
        "no se proponen: salen del perfil (RF-111)."
    )
    created_at: datetime
    updated_at: datetime


class AiConsentRead(BaseModel):
    provider: AiProvider
    granted: bool = Field(
        description="Vigente: dado sobre la versión actual del texto y sin retirar."
    )
    granted_at: datetime | None
    revoked_at: datetime | None


class AiConsentsRead(BaseModel):
    text_version: int = Field(
        description="Versión del texto del consentimiento. Si sube, el anterior ya "
        "no vale y hay que volver a darlo (RF-154).",
        examples=[AI_CONSENT_VERSION],
    )
    platform_provider: AiProvider | None = Field(
        description="Proveedor de los usos gratuitos de esta instalación, al que "
        "se envían los datos. `null`: sin uso gratuito."
    )
    platform_model: str | None = Field(examples=["openai/gpt-oss-120b"])
    consents: list[AiConsentRead] = Field(
        description="Uno por cada proveedor al que el usuario ha dado (o retirado) "
        "su consentimiento."
    )
