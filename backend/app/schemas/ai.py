import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.ai import (
    AI_CONSENT_VERSION,
    AiProvider,
    AiTask,
    CvProposal,
    KeySource,
    ProposalErrorCode,
    ProposalLanguage,
    ProposalStatus,
    ValidatedBullet,
    ValidatedExperience,
)
from app.domain.documents import TEMPLATE_MAX_LENGTH
from app.domain.profile import (
    BULLET_MAX_LENGTH,
    MAX_BULLETS_PER_ENTRY,
    MAX_ENTRIES,
    MAX_SKILLS,
    SUMMARY_MAX_LENGTH,
    EntryKind,
)
from app.schemas.common import OptionalShortText


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
        "no se proponen: salen del perfil (RF-111). `requirements` (desde el prompt "
        "`cv/v2`; `null` en las anteriores) son los requisitos de la oferta, con las "
        "palabras con que se buscarían en un CV y los elementos del perfil que los "
        "demuestran; el porcentaje de encaje lo calcula el cliente con ellos."
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


class ReviewedBullet(BaseModel):
    bullet_id: uuid.UUID = Field(description="Un logro de esa experiencia del perfil.")
    text: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=BULLET_MAX_LENGTH
        ),
    ]


class ReviewedExperience(BaseModel):
    entry_id: uuid.UUID = Field(description="Una experiencia del perfil.")
    bullets: list[ReviewedBullet] = Field(max_length=MAX_BULLETS_PER_ENTRY)


class ReviewedCvProposal(BaseModel):
    """La propuesta tal como queda tras revisarla (RF-113): el usuario puede
    reescribir el resumen y los logros, quitar experiencias, logros o habilidades y
    cambiar su orden. Los ids siguen siendo los del perfil."""

    summary: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=SUMMARY_MAX_LENGTH
        ),
    ]
    experiences: list[ReviewedExperience] = Field(
        min_length=1, max_length=MAX_ENTRIES[EntryKind.EXPERIENCE]
    )
    skill_ids: list[uuid.UUID] = Field(max_length=MAX_SKILLS)

    def to_domain(self) -> CvProposal:
        return CvProposal(
            summary=self.summary,
            experiences=[
                ValidatedExperience(
                    entry_id=experience.entry_id,
                    bullets=[
                        ValidatedBullet(bullet_id=bullet.bullet_id, text=bullet.text)
                        for bullet in experience.bullets
                    ],
                )
                for experience in self.experiences
            ],
            skill_ids=list(dict.fromkeys(self.skill_ids)),
            gaps=[],
        )


class AiProposalDocumentCreate(BaseModel):
    """Generar el CV adaptado desde una propuesta revisada (RF-113, RF-114)."""

    design: Annotated[
        str, StringConstraints(min_length=1, max_length=TEMPLATE_MAX_LENGTH)
    ] = Field(description="Clave del diseño (`GET /documents/cv-designs`).")
    name: OptionalShortText = Field(
        default=None,
        description="Nombre visible en la biblioteca. Sin él, `CV <puesto> – "
        "<empresa>`.",
    )
    proposal: ReviewedCvProposal
