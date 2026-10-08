import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    model_validator,
)

from app.domain.ai import (
    AI_CONSENT_VERSION,
    LETTER_LINE_MAX_LENGTH,
    LETTER_PARAGRAPH_MAX_LENGTH,
    MAX_LETTER_PARAGRAPHS,
    AiProvider,
    AiTask,
    CoverLetterProposal,
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
        description="`cv` (adaptar el CV, RF-110) o `cover_letter` (la carta de "
        "presentación, RF-114). Cada una tiene su propia cuota gratuita."
    )
    language: ProposalLanguage = Field(
        description="Idioma en que se escribe la propuesta: el resumen y los logros del "
        "CV, o la carta."
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
    proposal: CvProposal | CoverLetterProposal | None = Field(
        description="Solo en `succeeded`. Con `kind` `cover_letter`, la carta: saludo, "
        "párrafos con las referencias al perfil en que se apoya cada uno y despedida. "
        "Con `cv`, cada experiencia, logro y habilidad "
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


LetterLine = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=LETTER_LINE_MAX_LENGTH
    ),
]


class ReviewedCoverLetter(BaseModel):
    """La carta tal como queda tras revisarla (RF-113): todo su texto es editable
    y se pueden quitar o reordenar párrafos. Las fuentes no se envían: solo sirven
    para revisar."""

    greeting: LetterLine
    paragraphs: list[
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=1,
                max_length=LETTER_PARAGRAPH_MAX_LENGTH,
            ),
        ]
    ] = Field(min_length=1, max_length=MAX_LETTER_PARAGRAPHS)
    closing: LetterLine


class AiProposalDocumentCreate(BaseModel):
    """Generar el CV adaptado o la carta desde una propuesta revisada (RF-113,
    RF-114). Lleva `proposal` si la propuesta es de CV y `letter` si es de carta."""

    design: Annotated[
        str, StringConstraints(min_length=1, max_length=TEMPLATE_MAX_LENGTH)
    ] = Field(description="Clave del diseño (`GET /documents/cv-designs`).")
    name: OptionalShortText = Field(
        default=None,
        description="Nombre visible en la biblioteca. Sin él, `CV <puesto> – "
        "<empresa>` o `Carta <puesto> – <empresa>`.",
    )
    proposal: ReviewedCvProposal | None = Field(
        default=None, description="El CV revisado, si la propuesta es de `cv`."
    )
    letter: ReviewedCoverLetter | None = Field(
        default=None, description="La carta revisada, si es de `cover_letter`."
    )

    @model_validator(mode="after")
    def _one_content(self) -> "AiProposalDocumentCreate":
        if (self.proposal is None) == (self.letter is None):
            raise ValueError("send either proposal or letter")
        return self


# --- Claves propias (RF-151, ia.md §7) ------------------------------------------


class AiKeyRead(BaseModel):
    """Una clave guardada, sin la clave: nunca vuelve al cliente (ia.md §7)."""

    model: str = Field(description="El modelo elegido para esta clave.")
    last4: str = Field(description="Los 4 últimos caracteres, para reconocerla.")
    validated_at: datetime = Field(description="Cuándo se comprobó que funcionaba.")
    model_allowed: bool = Field(
        description="`false` si quien despliega retiró ese modelo de la lista: hay "
        "que elegir otro antes de usar la clave."
    )


class AiProviderOption(BaseModel):
    provider: AiProvider
    models: list[str] = Field(
        description="Los modelos que se pueden elegir con una clave de este "
        "proveedor; el primero es el recomendado."
    )
    key: AiKeyRead | None = Field(description="La clave guardada, si hay.")


class AiKeysRead(BaseModel):
    own_keys_enabled: bool = Field(
        description="Si esta instalación admite claves propias."
    )
    providers: list[AiProviderOption] = Field(
        description="Los proveedores con los que se puede usar una clave propia."
    )
    active_provider: AiProvider | None = Field(
        description="Con qué clave propia se usa la IA. `null`: los usos gratuitos "
        "de la plataforma."
    )


class AiKeySave(BaseModel):
    api_key: SecretStr = Field(
        description="La clave de API del proveedor. Se comprueba con una llamada "
        "mínima, se guarda cifrada y nunca se devuelve."
    )
    model: str | None = Field(
        default=None,
        max_length=100,
        description="Uno de `models` del proveedor. Sin él, el recomendado.",
    )


class AiKeyModelUpdate(BaseModel):
    model: Annotated[str, StringConstraints(min_length=1, max_length=100)]


class AiActiveProviderUpdate(BaseModel):
    provider: AiProvider | None = Field(
        description="El proveedor de una clave guardada, o `null` para volver a los "
        "usos gratuitos de la plataforma."
    )
